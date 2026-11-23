package probe.ui

import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import probe.api.Note

@Composable
fun NoteRow(note: Note) {
    Text(note.text)
}
