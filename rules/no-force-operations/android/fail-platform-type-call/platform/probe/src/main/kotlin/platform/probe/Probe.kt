package platform.probe

import android.app.Activity

/** Activity.getIntent() has no nullability annotation, so Kotlin sees Intent! and lets this crash on null. */
class Launch(private val activity: Activity) {
    fun fixture(): String? = activity.intent.getStringExtra("fixture")
}
