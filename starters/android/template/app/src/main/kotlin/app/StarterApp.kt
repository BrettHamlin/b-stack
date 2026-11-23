package app

import android.app.Application
import kotlinx.coroutines.Dispatchers
import platform.files.FileTallyStore
import tally.api.TallyStore
import java.io.File

/** The shipped app's composition root: services that live as long as the process, built once (not per Activity,
 * which rotation recreates). Real services only. */
class StarterApp : Application() {
    val tallyStore: TallyStore by lazy { FileTallyStore(File(filesDir, "tally.txt"), Dispatchers.IO) }
}
