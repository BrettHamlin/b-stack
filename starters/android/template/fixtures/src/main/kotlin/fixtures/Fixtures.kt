package fixtures

import android.content.Context
import kotlinx.coroutines.CoroutineDispatcher
import platform.files.FileTallyStore
import tally.api.Stored
import tally.api.Tally
import tally.api.TallyStore
import java.io.File

/** Test-mode setups, by name. Journeys launch app-verify with one; the shipped app can't use this module. */
enum class Fixture {
    /** An empty tally, saved in a fresh file. */
    Standard,

    /** The tally `apple 2, pear 1`, already saved when the app starts. */
    Saved,

    /** The tally `apple 2`, already saved, on the real store, except every save fails. */
    FailingSaves,

    /** A saved file the store can't read. */
    Unreadable,
}

fun fixtureNamed(name: String?): Fixture? = Fixture.entries.firstOrNull { it.name == (name ?: Fixture.Standard.name) }

/** The store [fixture] runs on, in the app's files folder. With [reset], it starts from the fixture's data; without it
 * (a relaunch), it keeps what the last launch saved. */
fun tallyStore(fixture: Fixture, context: Context, io: CoroutineDispatcher, reset: Boolean): TallyStore {
    val dir = File(context.filesDir, "fixture")
    val file = File(dir, "tally.json")
    if (reset) {
        dir.deleteRecursively()
        dir.mkdirs()
        when (fixture) {
            Fixture.Standard -> Unit
            Fixture.Saved -> file.writeText("""{"counts":{"apple":2,"pear":1}}""")
            Fixture.FailingSaves -> file.writeText("""{"counts":{"apple":2}}""")
            Fixture.Unreadable -> file.writeText("not a tally\n")
        }
    }
    val real = FileTallyStore(file, io)
    return when (fixture) {
        Fixture.Standard, Fixture.Saved, Fixture.Unreadable -> real
        Fixture.FailingSaves -> FailingSaves(real)
    }
}

private class FailingSaves(private val real: TallyStore) : TallyStore {
    override suspend fun load(): Stored<Tally> = real.load()

    override suspend fun save(tally: Tally): Stored<Unit> = Stored.Failed
}
