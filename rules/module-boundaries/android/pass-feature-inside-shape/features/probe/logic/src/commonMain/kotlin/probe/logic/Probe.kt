package probe.logic

import probe.api.Reading
import probe.api.ReadingSource

class ProbeLogic(private val source: ReadingSource) {
    suspend fun doubled(): Reading = Reading(source.read().value * 2)
}
