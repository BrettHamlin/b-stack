package probe.logic

fun parse(text: String): Int = text.toIntOrNull() ?: error("not a number")
