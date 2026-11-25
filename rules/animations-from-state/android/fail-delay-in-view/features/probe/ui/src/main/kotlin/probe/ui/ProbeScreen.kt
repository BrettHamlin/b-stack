package probe.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay

/** Grows the marker after a fixed pause, timed by hand. */
@Composable
fun Marker(hit: Boolean) {
    var big by remember { mutableStateOf(false) }
    LaunchedEffect(hit) {
        delay(300)
        big = hit
    }
    Box(Modifier.size(if (big) 48.dp else 24.dp))
}
