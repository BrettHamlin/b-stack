package platform.probe

import android.content.Context
import android.os.Build

class Attribution(private val context: Context) {
    fun tag(): String? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) context.attributionTag else null
}
