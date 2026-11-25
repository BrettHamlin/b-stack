package platform.files

import android.content.Context
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import tally.api.ItemName
import tally.api.Stored
import tally.api.Tally
import tally.api.TallyStore
import java.io.File
import java.io.IOException

/** Keeps the tally in [file] as JSON (kotlinx.serialization). A save writes a new file and renames it into place, so
 * a failed save leaves the old tally. A file that isn't a tally (not JSON, a name a tally can't have, a count below 1)
 * fails to load, so it's never replaced by a count from nothing. File work runs on [io]. */
class FileTallyStore(private val file: File, private val io: CoroutineDispatcher) : TallyStore {
    /** The store in the app's own files folder. */
    constructor(context: Context, io: CoroutineDispatcher) : this(File(context.filesDir, "tally.json"), io)

    override suspend fun load(): Stored<Tally> = withContext(io) {
        try {
            if (!file.exists()) return@withContext Stored.Done(Tally.Empty)
            val tally = Json.decodeFromString(Tally.serializer(), file.readText())
            val valid = tally.counts.all { (name, count) -> ItemName.parse(name.value) == name && count >= 1 }
            if (valid) Stored.Done(tally) else Stored.Failed
        } catch (_: IllegalArgumentException) {
            Stored.Failed // not JSON, or not a tally (kotlinx.serialization's SerializationException is one)
        } catch (_: IOException) {
            Stored.Failed
        }
    }

    override suspend fun save(tally: Tally): Stored<Unit> = withContext(io) {
        try {
            val staged = File(file.parentFile, "${file.name}.new")
            staged.writeText(Json.encodeToString(Tally.serializer(), tally))
            if (!staged.renameTo(file)) return@withContext Stored.Failed
            Stored.Done(Unit)
        } catch (_: IOException) {
            Stored.Failed
        }
    }
}
