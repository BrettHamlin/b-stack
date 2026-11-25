package probe.ui

import androidx.compose.animation.core.animateDpAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/** Grows the marker when it's hit: the size follows the state, and Compose animates the change. */
@Composable
fun Marker(hit: Boolean) {
    val size by animateDpAsState(if (hit) 48.dp else 24.dp, label = "marker")
    Box(Modifier.size(size))
}
