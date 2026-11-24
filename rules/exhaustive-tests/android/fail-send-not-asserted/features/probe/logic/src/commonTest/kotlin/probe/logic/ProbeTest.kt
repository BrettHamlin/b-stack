package probe.logic

import app.cash.turbine.test
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals

class ProbeTest {
    @Test
    fun bumpsTwice() = runTest {
        val counter = Counter()

        counter.state.test {
            assertEquals(0, awaitItem())
            counter.send(CounterAction.Bump)
            counter.send(CounterAction.Bump)
            assertEquals(2, awaitItem())
        }
    }
}
