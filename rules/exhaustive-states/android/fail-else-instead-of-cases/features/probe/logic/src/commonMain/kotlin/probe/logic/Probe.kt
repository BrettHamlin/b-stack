package probe.logic

import probe.api.Phase

fun label(phase: Phase): String = when (phase) {
    Phase.Idle -> "idle"
    else -> "busy"
}
