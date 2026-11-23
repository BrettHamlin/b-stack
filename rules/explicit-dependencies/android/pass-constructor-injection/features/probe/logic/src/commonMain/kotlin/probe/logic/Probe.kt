package probe.logic

import probe.api.NotesClient

const val LIMIT = 10

sealed interface Loaded {
    data object Empty : Loaded

    data class Notes(val notes: List<String>) : Loaded
}

class NotesModel(private val client: NotesClient) {
    suspend fun load(): Loaded = client.load().take(LIMIT).let { if (it.isEmpty()) Loaded.Empty else Loaded.Notes(it) }

    companion object {
        const val TITLE = "Notes"
        val defaultLimit: Int get() = LIMIT

        @Deprecated(message = "Use defaultLimit = LIMIT instead")
        val oldLimit: Int get() = LIMIT
    }
}
