package probe.ui

import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import probe.api.NotesClient

@Composable
fun Notes(client: NotesClient) {
    Text(client.toString())
}
