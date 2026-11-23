package probe.logic

import app.cash.turbine.test
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals

import kotlinx.coroutines.flow.first
class ProbeTest {
    @Test
    fun bumps() = runTest {
        val counter = Counter()

        counter.bump()
        assertEquals(1, counter.state.first())
    }
}
