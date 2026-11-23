package probe.ui

import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import coreui.uiId
import probe.api.ProbeUi

@Composable
fun Go(onGo: () -> Unit) {
    Button(onClick = onGo, modifier = Modifier.uiId(ProbeUi.go)) { Text("Go") }
}
