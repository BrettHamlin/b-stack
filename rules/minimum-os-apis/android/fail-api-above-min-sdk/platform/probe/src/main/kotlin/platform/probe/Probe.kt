package platform.probe

import android.content.Context

/** Context.getAttributionTag is API 30; the app supports API 29. */
class Attribution(private val context: Context) {
    fun tag(): String? = context.attributionTag
}
