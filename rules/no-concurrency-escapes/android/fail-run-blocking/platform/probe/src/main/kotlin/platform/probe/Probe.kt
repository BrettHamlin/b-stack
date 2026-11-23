package platform.probe

import kotlinx.coroutines.runBlocking

class Loader(private val load: suspend () -> String) {
    fun now(): String = runBlocking { load() }
}
