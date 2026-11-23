package probe.ui

import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext

@Composable
fun SaveNote(note: String) {
    LocalContext.current.openFileOutput("note.txt", 0).use { it.write(note.toByteArray()) }
}
