package app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import tally.ui.TallyRoute

/** Shows the app's screens with the services StarterApp composed. */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val services = application as? StarterApp ?: return finish()
        setContent { MaterialTheme { Surface { TallyRoute(services.tallyStore) } } }
    }
}
