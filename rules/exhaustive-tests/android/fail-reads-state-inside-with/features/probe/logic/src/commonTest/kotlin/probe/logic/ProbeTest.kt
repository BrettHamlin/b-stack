package probe.logic

import app.cash.turbine.test
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals

class ProbeTest {
    @Test
    fun bumps() = runTest {
        val counter = Counter()

        with(counter) {
            bump()
            assertEquals(1, state.value)
        }
    }
}
