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

/** A wrapper's own field may be a primitive, whatever it's called. */
@JvmInline
value class ShipId(val id: Int)

data class Fleet(val id: ShipId, val shipIds: Set<ShipId>, val leaderId: PlayerId?, val size: Int)
