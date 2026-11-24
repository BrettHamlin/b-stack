package probe.logic

import probe.api.PlayerId
import probe.api.PlayerName

fun first(): String = PlayerName.parse("ada")?.let { describe(PlayerId(7), it) } ?: "no name"

fun describe(id: PlayerId, name: PlayerName): String = "${id.value}: ${name.value}"
