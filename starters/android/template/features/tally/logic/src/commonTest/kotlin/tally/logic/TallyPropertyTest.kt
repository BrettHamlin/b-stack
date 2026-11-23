package tally.logic

import app.cash.turbine.test
import kotlinx.coroutines.test.runTest
import tally.api.ItemName
import tally.api.Tally
import kotlin.random.Random
import kotlin.test.Test
import kotlin.test.assertEquals

/** 200 seeded random sequences of names and adds, each checked step by step against a model of the spec: a valid
 * name is counted and saved, an invalid one changes nothing but the problem shown. */
class TallyPropertyTest {
    private val names = listOf("apple", "pear", "fig", "", "two words", "x".repeat(33), "a-b_c")

    @Test
    fun matchesTheSpec() = runTest {
        repeat(200) { seed ->
            val random = Random(seed)
            val store = MemoryStore()
            val model = TallyModel(store, backgroundScope)
            var expected = TallyState(loading = false)
            model.state.test {
                assertEquals(TallyState(), awaitItem())
                assertEquals(expected, awaitItem())
                repeat(random.nextInt(1, 12)) { step ->
                    val raw = names[random.nextInt(names.size)]
                    if (raw != expected.name) {
                        model.send(TallyAction.NameChanged(raw))
                        expected = expected.copy(name = raw)
                        assertEquals(expected, awaitItem(), "seed $seed, step $step: typed \"$raw\"")
                    }
                    model.send(TallyAction.Add)
                    val name = ItemName.parse(raw)
                    if (name == null) {
                        if (expected.problem != TallyProblem.InvalidName) {
                            expected = expected.copy(problem = TallyProblem.InvalidName)
                            assertEquals(expected, awaitItem(), "seed $seed, step $step: added invalid \"$raw\"")
                        }
                    } else {
                        assertEquals(expected.copy(saving = true), awaitItem(), "seed $seed, step $step: saving")
                        val counts = expected.tally.counts
                        expected = expected.copy(
                            tally = Tally(counts + (name to (counts[name] ?: 0) + 1)),
                            name = "",
                            problem = null,
                        )
                        assertEquals(expected, awaitItem(), "seed $seed, step $step: added \"$raw\"")
                    }
                }
                assertEquals(expected.tally, store.current, "seed $seed: saved tally")
            }
        }
    }
}
