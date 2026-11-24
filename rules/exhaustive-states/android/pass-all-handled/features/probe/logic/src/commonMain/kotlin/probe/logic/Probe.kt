package probe.logic

import probe.api.Mode
import probe.api.Phase

fun label(phase: Phase): String = when (phase) {
    Phase.Idle -> "idle"
    Phase.Running -> "running"
    is Phase.Done -> "done: ${phase.score}"
}

fun speed(mode: Mode): Int = when (mode) {
    Mode.Easy -> 1
    Mode.Hard -> 2
}
