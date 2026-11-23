package probe.ui

import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import probe.api.Reading

@Composable
fun ReadingView(reading: Reading) {
    Text("${reading.value}")
}
