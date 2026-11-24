package probe.logic

fun value(result: Result<Int>): Int = result.getOrThrow()
