package probe.logic

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

class Counter {
    private val count = MutableStateFlow(0)
    val state: StateFlow<Int> = count.asStateFlow()

    fun bump() {
        count.update { it + 1 }
    }
}
