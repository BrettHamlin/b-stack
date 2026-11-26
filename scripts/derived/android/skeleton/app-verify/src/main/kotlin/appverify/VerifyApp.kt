package appverify

import android.app.Application
import android.os.StrictMode

/** The test-mode app's composition root. Disk or network work on
 * the main thread kills the app, so a journey fails instead of the shipped app stuttering. */
class VerifyApp : Application() {
    override fun onCreate() {
        super.onCreate()
        StrictMode.setThreadPolicy(
            StrictMode.ThreadPolicy.Builder().detectNetwork().detectDiskWrites().penaltyLog().penaltyDeath().build(),
        )
    }
}
