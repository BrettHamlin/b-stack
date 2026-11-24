package appverify

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import coreui.rememberModel
import fixtures.fixtureNamed
import tally.logic.TallyModel
import tally.ui.TallyRoute

/** Shows the same feature entry points as the shipped app, on the fixture's services. Journeys start it with
 * `bstack.fixture` (a fixtures.Fixture name) and `bstack.reset` (start from the fixture's data, rather than what the
 * last run left). */
class VerifyActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val app = application as? VerifyApp ?: return finish()
        val launch: Intent? = intent
        val fixture = fixtureNamed(launch?.getStringExtra("bstack.fixture"))
        val reset = savedInstanceState == null && launch?.getBooleanExtra("bstack.reset", false) == true
        val store = fixture?.let { app.tallyStore(it, reset) }
        setContent {
            MaterialTheme {
                Surface {
                    if (store == null) {
                        Text("Unknown fixture: ${launch?.getStringExtra("bstack.fixture")}")
                    } else {
                        TallyRoute(rememberModel("tally") { scope, saved -> TallyModel(store, scope, saved) })
                    }
                }
            }
        }
    }
}
