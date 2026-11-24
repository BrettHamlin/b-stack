package platform.probe

class Saver(private val save: suspend () -> Unit) {
    suspend fun trySave(): Boolean = runCatching { save() }.isSuccess
}
