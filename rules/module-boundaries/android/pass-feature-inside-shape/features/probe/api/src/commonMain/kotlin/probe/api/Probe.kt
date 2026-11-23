package probe.api

data class Reading(val value: Int)

interface ReadingSource {
    suspend fun read(): Reading
}
