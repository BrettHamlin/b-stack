package platform.probe

import probe.api.NotesClient

object Notes : NotesClient {
    override suspend fun load(): List<String> = emptyList()
}
