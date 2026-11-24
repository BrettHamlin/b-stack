package probe.ui

import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import probe.logic.ProbeAction
import probe.logic.ProbeAction.Picked
import probe.logic.ProbeModel
import probe.logic.ProbeMood
import probe.logic.ProbeState
import probe.logic.reachable


@Composable
fun ProbeRoute(model: ProbeModel) {
    val state by model.state.collectAsState()
    ProbeScreen(state, model::send)
}

@Composable
fun ProbeScreen(state: ProbeState, send: (ProbeAction) -> Unit) {
    Button(onClick = { send(Picked) }, enabled = reachable(state)) {
        Text(
            when (state.mood) {
                ProbeMood.Calm -> "Pick"
                ProbeMood.Busy -> "Busy"
            },
        )
    }
}
