package appverify

import android.content.Context

fun seed(context: Context) = context.filesDir.resolve("seed.txt").writeText("fig")
