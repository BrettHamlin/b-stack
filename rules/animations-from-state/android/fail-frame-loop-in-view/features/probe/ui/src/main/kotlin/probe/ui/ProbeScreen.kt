package probe.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/** Grows the marker frame by frame, by its own clock. */
@Composable
fun Marker(hit: Boolean) {
    var grown by remember { mutableFloatStateOf(0f) }
    LaunchedEffect(hit) {
        val start = withFrameNanos { it }
        while (grown < 1f) {
            withFrameNanos { now -> grown = minOf(1f, (now - start) / 300_000_000f) }
        }
    }
    Box(Modifier.size((24 + 24 * grown).dp))
}
