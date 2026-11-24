package probe.api

interface Store {
    suspend fun load(): List<String>?

    suspend fun loadOrEmpty(): List<String> = load().orEmpty()
}
