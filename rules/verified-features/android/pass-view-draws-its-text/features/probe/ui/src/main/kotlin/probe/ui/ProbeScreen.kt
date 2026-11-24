package probe.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics

/** The text journeys read is the text drawn; the description is for screen readers. */
@Composable
fun Cell(emoji: String, strength: Int) {
    val text = "strength $strength"
    Column(Modifier.semantics(mergeDescendants = true) { contentDescription = "Cruiser, $text"; role = Role.Button }) {
        Text(emoji)
        Text(text = text)
    }
}
