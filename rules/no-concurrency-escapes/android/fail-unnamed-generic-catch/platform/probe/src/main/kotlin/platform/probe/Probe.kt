package platform.probe

class Loader(private val fetch: suspend () -> String) {
    suspend fun load(): String? = try {
        fetch()
    } catch (_: Exception) {
        null
    }
}
