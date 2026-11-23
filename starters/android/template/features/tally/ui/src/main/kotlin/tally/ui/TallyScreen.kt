package tally.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import coreui.uiId
import tally.api.TallyStore
import tally.api.TallyUi
import tally.logic.TallyAction
import tally.logic.TallyModel
import tally.logic.TallyProblem
import tally.logic.TallyState
import tally.logic.entries

/** Holds the model across configuration changes; its scope ends when the screen is gone for good. */
private class TallyHolder(store: TallyStore) : ViewModel() {
    val model = TallyModel(store, viewModelScope)
}

/** The tally feature's entry point. Both apps call it, with the store each composes (real or fixture). */
@Composable
fun TallyRoute(store: TallyStore) {
    val holder = viewModel { TallyHolder(store) }
    val state by holder.model.state.collectAsState()
    TallyScreen(state, holder.model::send)
}

@Composable
fun TallyScreen(state: TallyState, send: (TallyAction) -> Unit) {
    Column(Modifier.fillMaxSize().safeDrawingPadding().padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(
                value = state.name,
                onValueChange = { send(TallyAction.NameChanged(it)) },
                label = { Text("Item name") },
                enabled = state.canAdd,
                singleLine = true,
                modifier = Modifier.weight(1f).uiId(TallyUi.name),
            )
            Button(
                onClick = { send(TallyAction.Add) },
                enabled = state.canAdd,
                modifier = Modifier.uiId(TallyUi.add),
            ) { Text("Add") }
        }
        Text(problemText(state.problem), color = MaterialTheme.colorScheme.error, modifier = Modifier.uiId(TallyUi.error))
        val items = entries(state.tally)
        Column(Modifier.uiId(TallyUi.items)) {
            if (items.isEmpty()) Text("(empty)")
            items.forEachIndexed { row, (name, count) -> Text("${name.value} $count", Modifier.uiId(TallyUi.item.at(row))) }
        }
    }
}

private fun problemText(problem: TallyProblem?): String = when (problem) {
    null -> ""
    TallyProblem.LoadFailed -> "The saved tally couldn't be read."
    TallyProblem.InvalidName -> "Names are 1 to 32 letters, digits, - or _."
    TallyProblem.SaveFailed -> "Couldn't save. The tally is unchanged."
}
