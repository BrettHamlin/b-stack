package probe.logic

import probe.api.Mode

fun speed(mode: Mode): Int = when (mode) {
    Mode.Easy -> 1
    Mode.Hard -> 2
    else -> 3
}
