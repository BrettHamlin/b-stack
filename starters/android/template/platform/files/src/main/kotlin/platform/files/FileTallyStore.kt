package platform.files

import android.content.Context
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.withContext
import tally.api.ItemName
import tally.api.Stored
import tally.api.Tally
import tally.api.TallyStore
import java.io.File
import java.io.IOException

/** Keeps the tally in [file], one `name<TAB>count` line per item. A save writes a new file and renames it into place,
 * so a failed save leaves the old tally. File work runs on [io]. */
class FileTallyStore(private val file: File, private val io: CoroutineDispatcher) : TallyStore {
    /** The store in the app's own files folder. */
    constructor(context: Context, io: CoroutineDispatcher) : this(File(context.filesDir, "tally.txt"), io)

    override suspend fun load(): Stored<Tally> = withContext(io) {
        try {
            if (!file.exists()) return@withContext Stored.Done(Tally.Empty)
            val counts = file.readLines().filter { it.isNotBlank() }.map { line ->
                val parts = line.split('\t')
                val name = ItemName.parse(parts.getOrElse(0) { "" })
                val count = parts.getOrNull(1)?.toIntOrNull()
                if (parts.size != 2 || name == null || count == null || count < 1) return@withContext Stored.Failed
                name to count
            }
            Stored.Done(Tally(counts.toMap()))
        } catch (_: IOException) {
            Stored.Failed
        }
    }

    override suspend fun save(tally: Tally): Stored<Unit> = withContext(io) {
        try {
            val staged = File(file.parentFile, "${file.name}.new")
            staged.writeText(tally.counts.entries.joinToString("") { "${it.key.value}\t${it.value}\n" })
            if (!staged.renameTo(file)) return@withContext Stored.Failed
            Stored.Done(Unit)
        } catch (_: IOException) {
            Stored.Failed
        }
    }
}
