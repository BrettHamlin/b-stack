package probe.ui

import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag

@Composable
fun Go(onGo: () -> Unit) {
    Button(onClick = onGo, modifier = Modifier.testTag("probe.go")) { Text("Go") }
}
