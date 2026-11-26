package tally.api

import kotlinx.serialization.Serializable
import kotlin.jvm.JvmInline

/** An item's name: 1 to 32 letters, digits, `-` or `_`. Made only by [parse], so every ItemName is valid. */
@Serializable
@JvmInline
value class ItemName private constructor(val value: String) {
    companion object {
        private val valid = Regex("^[A-Za-z0-9_-]{1,32}$")

        fun parse(raw: String): ItemName? = if (valid.matches(raw)) ItemName(raw) else null
    }
}

/** How many times each item was recorded. Saved as JSON (kotlinx.serialization). */
@Serializable
data class Tally(val counts: Map<ItemName, Int>) {
    companion object {
        val Empty = Tally(emptyMap())
    }
}

/** What a store call gives back: the value, or that the storage failed. */
sealed interface Stored<out T> {
    data class Done<T>(val value: T) : Stored<T>

    data object Failed : Stored<Nothing>
}

/** Where the tally is kept. A platform module implements it; the composition root picks one. */
interface TallyStore {
    suspend fun load(): Stored<Tally>

    suspend fun save(tally: Tally): Stored<Unit>
}
