package probe.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.AnnotatedString

@Composable
fun Field(value: String) {
    Box(Modifier.semantics { this[SemanticsProperties.EditableText] = AnnotatedString(value) }) {
        Text("*".repeat(value.length))
    }
}
