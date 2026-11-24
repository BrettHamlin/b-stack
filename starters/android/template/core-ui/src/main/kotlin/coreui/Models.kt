package coreui

import androidx.compose.runtime.Composable
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.createSavedStateHandle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import core.Saved
import kotlinx.coroutines.CoroutineScope

private class ModelHolder<M>(handle: SavedStateHandle, create: (CoroutineScope, Saved) -> M) : ViewModel() {
    val model: M = create(viewModelScope, HandleSaved(handle))
}

private class HandleSaved(private val handle: SavedStateHandle) : Saved {
    override fun get(key: String): String? = handle.get<String>(key)

    override fun set(key: String, value: String) {
        handle[key] = value
    }
}

/** The model [create] builds, kept across configuration changes (rotation), given a scope that ends when the screen
 * is gone for good and a [Saved] that survives the process ending in the background. The composition roots call it
 * with the services each app composed:
 * `TallyRoute(rememberModel("tally") { scope, saved -> TallyModel(services.tallyStore, scope, saved) })`. */
@Composable
fun <M> rememberModel(key: String, create: (CoroutineScope, Saved) -> M): M =
    viewModel(key = key) { ModelHolder(createSavedStateHandle(), create) }.model
