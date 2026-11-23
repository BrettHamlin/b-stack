package tally.logic

import app.cash.turbine.test
import kotlinx.coroutines.test.runTest
import tally.api.ItemName
import tally.api.Tally
import kotlin.test.Test
import kotlin.test.assertEquals

class TallyModelTest {
    private val apple = ItemName.parse("apple") ?: error("valid name")

    @Test
    fun recordingCountsAndSaves() = runTest {
        val store = MemoryStore()
        val model = TallyModel(store, backgroundScope)
        model.state.test {
            assertEquals(TallyState(), awaitItem())
            assertEquals(TallyState(loading = false), awaitItem())
            model.send(TallyAction.NameChanged("apple"))
            assertEquals(TallyState(name = "apple", loading = false), awaitItem())
            model.send(TallyAction.Add)
            assertEquals(TallyState(name = "apple", loading = false, saving = true), awaitItem())
            val saved = Tally(mapOf(apple to 1))
            assertEquals(TallyState(tally = saved, loading = false), awaitItem())
            assertEquals(saved, store.current)
        }
    }

    @Test
    fun failedSaveKeepsTheOldTally() = runTest {
        val before = Tally(mapOf(apple to 2))
        val store = MemoryStore(before, failSaves = true)
        val model = TallyModel(store, backgroundScope)
        model.state.test {
            assertEquals(TallyState(), awaitItem())
            assertEquals(TallyState(tally = before, loading = false), awaitItem())
            model.send(TallyAction.NameChanged("apple"))
            assertEquals(TallyState(tally = before, name = "apple", loading = false), awaitItem())
            model.send(TallyAction.Add)
            assertEquals(TallyState(tally = before, name = "apple", loading = false, saving = true), awaitItem())
            assertEquals(
                TallyState(tally = before, name = "apple", loading = false, problem = TallyProblem.SaveFailed),
                awaitItem(),
            )
            assertEquals(before, store.current)
        }
    }

    @Test
    fun badNameIsRefused() = runTest {
        val store = MemoryStore()
        val model = TallyModel(store, backgroundScope)
        model.state.test {
            assertEquals(TallyState(), awaitItem())
            assertEquals(TallyState(loading = false), awaitItem())
            model.send(TallyAction.NameChanged("no spaces"))
            assertEquals(TallyState(name = "no spaces", loading = false), awaitItem())
            model.send(TallyAction.Add)
            assertEquals(
                TallyState(name = "no spaces", loading = false, problem = TallyProblem.InvalidName),
                awaitItem(),
            )
            assertEquals(Tally.Empty, store.current)
        }
    }

    @Test
    fun aFailedLoadBlocksAdding() = runTest {
        val before = Tally(mapOf(apple to 2))
        val store = MemoryStore(before, failLoads = true)
        val model = TallyModel(store, backgroundScope)
        model.state.test {
            assertEquals(TallyState(), awaitItem())
            assertEquals(TallyState(loading = false, problem = TallyProblem.LoadFailed), awaitItem())
            model.send(TallyAction.NameChanged("apple"))
            assertEquals(TallyState(name = "apple", loading = false, problem = TallyProblem.LoadFailed), awaitItem())
            model.send(TallyAction.Add)
            assertEquals(before, store.current)
        }
    }
}
