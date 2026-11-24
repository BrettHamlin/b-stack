package app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import coreui.rememberModel
import greeting.logic.GreetingModel
import greeting.ui.GreetingRoute

/** Shows each feature's screen with a model built from StarterApp's services. */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface { GreetingRoute(rememberModel("greeting") { scope, saved -> GreetingModel(scope, saved) }) }
            }
        }
    }
}
