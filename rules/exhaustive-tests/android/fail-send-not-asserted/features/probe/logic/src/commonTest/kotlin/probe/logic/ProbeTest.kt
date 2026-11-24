package probe.logic

import app.cash.turbine.test
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.time.Duration.Companion.seconds

class ProbeTest {
    @Test
    fun bumpsTwice() = runTest {
        val counter = Counter()

        counter.state.test(timeout = maxOf(5.seconds, 1.seconds)) {
            assertEquals(0, awaitItem())
            counter.send(CounterAction.Bump)
            counter.send(CounterAction.Bump)
            assertEquals(2, awaitItem())
        }
    }
}
