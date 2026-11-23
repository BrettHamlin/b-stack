package probe.logic

import android.content.Context

fun prefs(context: Context) = context.getSharedPreferences("probe", 0)
