package probe.logic

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

enum class ProbeMood { Calm, Busy }

data class ProbeState(val picks: Int = 0, val mood: ProbeMood = ProbeMood.Calm) {
    /** Whether another pick is allowed: worked out on the state, where the logic's tests see it. */
    val canPick: Boolean get() = Pathfinder(picks).open
}

/** How picks are worked out: the state uses it in a getter, which doesn't make it a state type. */
class Pathfinder(private val picks: Int) {
    val open: Boolean get() = picks < 3
}

sealed interface ProbeAction {
    data object Picked : ProbeAction
}

class ProbeModel(start: ProbeState = ProbeState()) {
    private val current = MutableStateFlow(start)
    val state: StateFlow<ProbeState> = current.asStateFlow()

    fun send(action: ProbeAction) {
        when (action) {
            ProbeAction.Picked -> current.update { it.copy(picks = it.picks + 1) }
        }
    }
}

