package probe.logic

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class Counter {
    private val count = MutableStateFlow(0)
    val uiState: StateFlow<Int> = count.asStateFlow()
}
