package probe.logic

import probe.api.PlayerId
import probe.api.PlayerName

fun first(): String = describe(7, PlayerName.parse("ada") ?: return "")

fun describe(id: PlayerId, name: PlayerName): String = "${id.value}: ${name.value}"
