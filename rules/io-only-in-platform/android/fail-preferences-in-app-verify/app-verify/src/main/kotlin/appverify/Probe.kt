package appverify

import android.content.Context

fun seen(context: Context): Boolean = context.getSharedPreferences("probe", 0).getBoolean("seen", false)
