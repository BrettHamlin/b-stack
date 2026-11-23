package probe.api

@Deprecated("Use saveAll, which writes every change at once and can be cancelled.", ReplaceWith("saveAll(items)"), DeprecationLevel.ERROR)
fun saveEach(items: List<String>): Int = items.size

fun saveAll(items: List<String>): Int = items.size
