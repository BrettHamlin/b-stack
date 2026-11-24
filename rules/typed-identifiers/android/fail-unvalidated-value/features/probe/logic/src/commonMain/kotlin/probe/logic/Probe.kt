package probe.logic

import probe.api.PlayerId
import probe.api.PlayerName
import probe.api.describe

fun first(): String = describe(PlayerId(7), PlayerName(""))
