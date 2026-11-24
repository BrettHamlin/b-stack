package platform.probe

import probe.api.Mode

fun speed(mode: Mode): Int = when (mode) {
    Mode.Easy -> 1
    else -> 2
}
