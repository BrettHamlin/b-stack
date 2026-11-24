package probe.ui

import java.io.File

fun readNotes(dir: File): String = File(dir, "notes.txt").readText()
