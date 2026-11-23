package probe.api

interface NotesClient {
    suspend fun load(): List<String>
}
