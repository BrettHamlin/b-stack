package probe.ui

import probe.api.NotesClient

class Cached(private val notes: List<String>) : NotesClient {
    override suspend fun load(): List<String> = notes
}
