package probe.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp

/** A highlight drawn as a stroke, which journeys can't read as text: the cell says what it means in its description,
 * which a journey checks with describes() and a screen reader speaks. */
@Composable
fun Cell(reachable: Boolean) {
    Box(Modifier.size(48.dp).semantics { contentDescription = if (reachable) "Open space, can move here" else "Open space" }) {
        Canvas(Modifier.size(48.dp)) {
            drawCircle(if (reachable) Color.Green else Color.Gray, style = Stroke(3.dp.toPx()))
        }
    }
}
