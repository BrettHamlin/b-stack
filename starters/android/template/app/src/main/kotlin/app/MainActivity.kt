package app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import coreui.rememberModel
import tally.logic.TallyModel
import tally.ui.TallyRoute

/** Shows each feature's screen with a model built from StarterApp's services. */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val services = application as? StarterApp ?: return finish()
        setContent {
            MaterialTheme {
                Surface { TallyRoute(rememberModel("tally") { scope -> TallyModel(services.tallyStore, scope) }) }
            }
        }
    }
}
