package probe.logic

import app.cash.turbine.test
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals

class ProbeTest {
    @Test
    fun picksTwice() = runTest {
        val model = ProbeModel()
        model.send(ProbeAction.Picked)
        model.send(ProbeAction.Picked)
        // Subscribed after both picks: only the last state is seen, so a wrong first pick passes.
        model.state.test {
            assertEquals(ProbeState(picks = 2), awaitItem())
        }
    }
}
