package probe.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.text
import androidx.compose.ui.text.AnnotatedString

@Composable
fun Cell(strength: Int) {
    Box(Modifier.clearAndSetSemantics { text = AnnotatedString("strength $strength") }) {
        Text("🚀")
    }
}
