package platform.probe

sealed interface Loaded {
    data class Done(val text: String) : Loaded

    data object Failed : Loaded
}

class Loader(private val fetch: suspend () -> String) {
    suspend fun load(): Loaded = try {
        Loaded.Done(fetch())
    } catch (failure: Exception) {
        Loaded.Failed
    }
}
