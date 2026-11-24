package probe.logic

import probe.api.PlayerId
import probe.api.PlayerName

fun first(): String = describe(PlayerId(7), PlayerName(""))

fun describe(id: PlayerId, name: PlayerName): String = "${id.value}: ${name.value}"
