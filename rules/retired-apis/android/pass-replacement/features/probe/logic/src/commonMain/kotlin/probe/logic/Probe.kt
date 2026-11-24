package probe.logic

import probe.api.saveAll

fun store(items: List<String>): Int = saveAll(items)
