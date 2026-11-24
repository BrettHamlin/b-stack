package coreui

import androidx.compose.runtime.Composable
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.CoroutineScope

private class ModelHolder<M>(create: (CoroutineScope) -> M) : ViewModel() {
    val model: M = create(viewModelScope)
}

/** The model [create] builds, kept across configuration changes (rotation) and given a scope that ends when the
 * screen is gone for good. The composition roots call it with the services each app composed:
 * `TallyRoute(rememberModel("tally") { scope -> TallyModel(services.tallyStore, scope) })`. */
@Composable
fun <M> rememberModel(key: String, create: (CoroutineScope) -> M): M = viewModel(key = key) { ModelHolder(create) }.model
