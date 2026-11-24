package probe.api

interface ItemStore {
    @Deprecated("Use saveAll, which writes every change at once and can be cancelled.", ReplaceWith("saveAll(items)"), DeprecationLevel.ERROR)
    suspend fun saveEach(items: List<String>): Int

    suspend fun saveAll(items: List<String>): Int
}
