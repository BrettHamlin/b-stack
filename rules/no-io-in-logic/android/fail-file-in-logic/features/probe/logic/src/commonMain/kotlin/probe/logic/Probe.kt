package probe.logic

fun notes(): String = java.io.File("notes.txt").readText()
