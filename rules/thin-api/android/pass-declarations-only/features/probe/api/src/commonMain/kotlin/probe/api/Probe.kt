package probe.api

import core.UiId
import kotlin.jvm.JvmInline

@JvmInline
value class ShipId(val value: Int)

/** A name: 1 to 20 characters. Made only by [parse]. */
@JvmInline
value class ShipName private constructor(val value: String) {
    companion object {
        private val valid = Regex("^.{1,20}$")

        fun parse(raw: String): ShipName? = if (valid.matches(raw)) ShipName(raw) else null
    }
}

enum class Terrain(val displayName: String, val entryCost: Int) {
    Open("Open space", entryCost = 1),
    Asteroids("Asteroid field", entryCost = 2),
}

data class Hex(val col: Int, val row: Int)

data class Ship(val id: ShipId, val name: ShipName, val position: Hex) {
    companion object {
        const val FULL_STRENGTH = 8
    }
}

data class Board(val terrain: Map<Hex, Terrain>, val ships: List<Ship>) {
    companion object {
        val Empty = Board(emptyMap(), emptyList())
    }
}

sealed interface Loaded<out T> {
    data class Done<T>(val value: T) : Loaded<T>

    data object Failed : Loaded<Nothing>
}

interface BoardStore {
    suspend fun load(): Loaded<Board>

    suspend fun save(board: Board): Loaded<Unit>
}

object ProbeUi {
    val hex = UiId("probe.hex")
}
