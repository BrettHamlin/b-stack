package probe.logic

import probe.api.PlayerName
import probe.api.describe

fun first(): String = describe(7, PlayerName.parse("ada") ?: return "")
