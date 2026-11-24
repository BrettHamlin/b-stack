package tally.logic

import core.Saved
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import tally.api.ItemName
import tally.api.Stored
import tally.api.Tally
import tally.api.TallyStore

enum class TallyProblem { LoadFailed, InvalidName, SaveFailed }

data class TallyState(
    val tally: Tally = Tally.Empty,
    val name: String = "",
    val loading: Boolean = true,
    val saving: Boolean = false,
    val problem: TallyProblem? = null,
) {
    /** Whether Add (and the name field) can be used: not while loading or saving, nor after a failed load. */
    val canAdd: Boolean get() = !loading && !saving && problem != TallyProblem.LoadFailed
}

sealed interface TallyAction {
    data class NameChanged(val text: String) : TallyAction

    data object Add : TallyAction
}

/** The tally screen's state. The view renders [state] and sends actions; storage goes through [store], and work
 * runs in [scope], which the composition root owns (it outlives configuration changes). The name being typed is kept
 * in [saved] too, so it survives the system ending the app in the background. */
class TallyModel(private val store: TallyStore, private val scope: CoroutineScope, private val saved: Saved) {
    private val current = MutableStateFlow(TallyState())
    val state: StateFlow<TallyState> = current.asStateFlow()

    init {
        scope.launch {
            when (val loaded = store.load()) {
                is Stored.Done -> current.update { it.copy(tally = loaded.value, loading = false) }
                Stored.Failed -> current.update { it.copy(loading = false, problem = TallyProblem.LoadFailed) }
            }
        }
    }

    fun send(action: TallyAction) {
        when (action) {
            is TallyAction.NameChanged -> {
                saved[NAME] = action.text
                current.update { it.copy(name = action.text) }
            }
            TallyAction.Add -> add()
        }
    }

    // One record at a time: each one counts and saves, so two at once would lose a count.
    private fun add() {
        val before = current.value
        // After a failed load the saved tally is unknown: saving now would overwrite it with a count from nothing.
        if (before.loading || before.saving || before.problem == TallyProblem.LoadFailed) return
        val name = ItemName.parse(before.name)
        if (name == null) {
            current.update { it.copy(problem = TallyProblem.InvalidName) }
            return
        }
        val next = recorded(before.tally, name)
        current.update { it.copy(saving = true) }
        scope.launch {
            when (store.save(next)) {
                is Stored.Done -> {
                    saved[NAME] = ""
                    current.update { it.copy(tally = next, name = "", saving = false, problem = null) }
                }
                Stored.Failed -> current.update { it.copy(saving = false, problem = TallyProblem.SaveFailed) }
            }
        }
    }
}

private const val NAME = "name"

/** The tally after recording [name] once more. */
fun recorded(tally: Tally, name: ItemName): Tally =
    Tally(tally.counts + (name to (tally.counts[name] ?: 0) + 1))

/** Every item and its count, sorted by name. */
fun entries(tally: Tally): List<Pair<ItemName, Int>> = tally.counts.entries
    .sortedBy { it.key.value }
    .map { it.key to it.value }
