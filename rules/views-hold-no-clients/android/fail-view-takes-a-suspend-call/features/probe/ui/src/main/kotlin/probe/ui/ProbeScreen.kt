package probe.ui

import androidx.compose.material3.Text
import androidx.compose.runtime.Composable

@Composable
fun Notes(save: suspend (String) -> Unit, onBack: () -> Unit) {
    Text(save.toString() + onBack.toString())
}
