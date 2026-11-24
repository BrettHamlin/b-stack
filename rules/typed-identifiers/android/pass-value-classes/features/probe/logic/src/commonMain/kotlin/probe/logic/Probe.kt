package probe.logic

import probe.api.PlayerId
import probe.api.PlayerName
import probe.api.describe

fun first(): String = PlayerName.parse("ada")?.let { describe(PlayerId(7), it) } ?: "no name"
