package probe.logic

import app.cash.turbine.test
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals

class ProbeTest {
    @Test
    fun picksFromALaterState() = runTest {
        // A later starting state comes from the constructor, not from actions sent before subscribing.
        val model = ProbeModel(ProbeState(picks = 2, mood = ProbeMood.Busy))
        model.state.test {
            assertEquals(ProbeState(picks = 2, mood = ProbeMood.Busy), awaitItem())
            model.send(ProbeAction.Picked)
            assertEquals(ProbeState(picks = 3, mood = ProbeMood.Busy), awaitItem())
        }
        ProbeModel().state.test {
            assertEquals(ProbeState(), awaitItem())
        }
    }
}
