package probe.ui

import androidx.compose.runtime.staticCompositionLocalOf
import probe.api.NotesClient

val LocalNotes = staticCompositionLocalOf<NotesClient?> { null }
