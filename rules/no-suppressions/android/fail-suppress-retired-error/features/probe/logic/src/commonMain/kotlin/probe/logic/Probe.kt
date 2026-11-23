package probe.logic

import probe.api.saveEach

@Suppress("DEPRECATION_ERROR")
fun store(items: List<String>): Int = saveEach(items)
