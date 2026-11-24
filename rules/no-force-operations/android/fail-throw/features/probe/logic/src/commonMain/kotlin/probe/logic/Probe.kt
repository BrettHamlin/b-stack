package probe.logic

fun parse(text: String): Int = text.toIntOrNull() ?: throw IllegalStateException("not a number")
