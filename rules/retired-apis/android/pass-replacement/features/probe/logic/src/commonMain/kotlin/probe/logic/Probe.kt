package probe.logic

import probe.api.ItemStore

suspend fun store(items: List<String>, store: ItemStore): Int = store.saveAll(items)
