package platform.probe

import android.annotation.TargetApi
import android.content.Context

@TargetApi(30)
class Attribution(private val context: Context) {
    fun tag(): String? = context.attributionTag
}
