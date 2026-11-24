package platform.probe

import probe.api.NotesClient

data object Notes : NotesClient {
    override suspend fun load(): List<String> = emptyList()
}
