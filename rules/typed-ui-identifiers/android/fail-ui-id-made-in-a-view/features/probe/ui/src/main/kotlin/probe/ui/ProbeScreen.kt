package probe.ui

import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import core.UiId
import coreui.uiId

@Composable
fun Go(onGo: () -> Unit) {
    Button(onClick = onGo, modifier = Modifier.uiId(UiId("probe.go"))) { Text("Go") }
}
