package probe.ui

import java.io.File

fun lastNote(dir: File): String = File(dir, "note.txt").readText()
