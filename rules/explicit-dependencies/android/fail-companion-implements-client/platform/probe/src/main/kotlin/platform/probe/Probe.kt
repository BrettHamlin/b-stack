package platform.probe

import probe.api.NotesClient

class Notes {
    companion object : NotesClient {
        override suspend fun load(): List<String> = emptyList()
    }
}
