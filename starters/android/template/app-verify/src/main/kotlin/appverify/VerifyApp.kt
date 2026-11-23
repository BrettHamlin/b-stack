package appverify

import android.app.Application
import android.os.StrictMode
import fixtures.Fixture
import fixtures.tallyStore
import kotlinx.coroutines.Dispatchers
import tally.api.TallyStore

/** The test-mode app's composition root. The first launch in a process picks the fixture (journeys stop the app
 * before each launch), and the store lives as long as the process, as in the shipped app. Disk or network work on
 * the main thread kills the app, so a journey fails instead of the shipped app stuttering. */
class VerifyApp : Application() {
    private var store: TallyStore? = null

    override fun onCreate() {
        super.onCreate()
        StrictMode.setThreadPolicy(
            StrictMode.ThreadPolicy.Builder().detectNetwork().detectDiskWrites().penaltyLog().penaltyDeath().build(),
        )
    }

    /** The store for [fixture]; with [reset], its data starts from the fixture's (test setup, so it may write here). */
    fun tallyStore(fixture: Fixture, reset: Boolean): TallyStore = store ?: run {
        val policy = StrictMode.allowThreadDiskWrites()
        try {
            tallyStore(fixture, this, Dispatchers.IO, reset).also { store = it }
        } finally {
            StrictMode.setThreadPolicy(policy)
        }
    }
}
