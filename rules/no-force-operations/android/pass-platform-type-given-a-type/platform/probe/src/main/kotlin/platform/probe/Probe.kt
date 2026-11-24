package platform.probe

import android.app.Activity
import android.content.Intent
import java.util.Properties

class Launch(private val activity: Activity) {
    fun fixture(): String? {
        val launch: Intent? = activity.intent
        return launch?.getStringExtra("fixture")
    }

    fun longestName(): Int {
        val properties: Properties? = System.getProperties()
        val names: Set<String> = properties?.stringPropertyNames().orEmpty()
        var longest = 0
        for (name in names) longest = maxOf(longest, name.length)
        return longest
    }
}
