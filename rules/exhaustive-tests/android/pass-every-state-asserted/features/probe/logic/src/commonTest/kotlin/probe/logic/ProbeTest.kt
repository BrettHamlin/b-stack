package probe.logic

import app.cash.turbine.test
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals

class ProbeTest {
    @Test
    fun bumps() = runTest {
        val counter = Counter()

        counter.state.test {
            assertEquals(0, awaitItem())
            counter.bump()
            assertEquals(1, awaitItem())
            counter.bump()
            assertEquals(
                2,
                awaitItem(),
            )
            counter.bump()
            assertEquals(expected = 3, actual = this.awaitItem())
            counter.bump()
            assertEquals(expected = listOf(4).let { it.single() }, actual = awaitItem())
            counter.bump()
            assertEquals(buildList { add(5) }.sum(), awaitItem())
            counter.bump()
            assertEquals<Int>(6, awaitItem())
            counter.bump()
            assertEquals<Comparable<Int>>(7, awaitItem())
        }
    }
}
