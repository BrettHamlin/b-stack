package platform.probe

import java.io.File

class Notes(private val dir: File) {
    fun read(): String? = File(dir, "notes.txt").takeIf { it.exists() }?.readText()
}
