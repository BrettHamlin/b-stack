package probe.api

import kotlin.jvm.JvmInline

@JvmInline
value class PlayerId(val value: Int)

@JvmInline
value class PlayerName private constructor(val value: String) {
    companion object {
        fun parse(raw: String): PlayerName? = if (raw.isNotBlank() && raw.length <= 20) PlayerName(raw) else null
    }
}

fun describe(id: PlayerId, name: PlayerName): String = "${id.value}: ${name.value}"
