package platform.probe

import java.io.File

/** File.listFiles() returns null when the folder can't be read; Kotlin 2.4 knows (JDK nullability), and warnings are errors. */
class Folder(private val dir: File) {
    fun names(): List<String> = dir.listFiles().map { it.name }
}
