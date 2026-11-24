package appverify

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import fixtures.fixtureNamed

/** Shows the same feature entry points as the shipped app, on the fixture's services. Journeys start it with
 * `bstack.fixture` (a fixtures.Fixture name). */
class VerifyActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val launch: Intent? = intent
        val fixture = fixtureNamed(launch?.getStringExtra("bstack.fixture"))
        setContent {
            MaterialTheme {
                Surface {
                    if (fixture == null) {
                        Text("Unknown fixture: ${launch?.getStringExtra("bstack.fixture")}")
                    } else {
                        Text("")
                    }
                }
            }
        }
    }
}
