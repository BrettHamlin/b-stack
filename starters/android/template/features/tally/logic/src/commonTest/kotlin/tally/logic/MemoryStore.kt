package tally.logic

import tally.api.Stored
import tally.api.Tally
import tally.api.TallyStore

/** A store in memory; [failSaves] makes every save fail, [failLoads] every load. */
class MemoryStore(
    private var saved: Tally = Tally.Empty,
    private val failSaves: Boolean = false,
    private val failLoads: Boolean = false,
) : TallyStore {
    val current: Tally get() = saved

    override suspend fun load(): Stored<Tally> = if (failLoads) Stored.Failed else Stored.Done(saved)

    override suspend fun save(tally: Tally): Stored<Unit> {
        if (failSaves) return Stored.Failed
        saved = tally
        return Stored.Done(Unit)
    }
}
