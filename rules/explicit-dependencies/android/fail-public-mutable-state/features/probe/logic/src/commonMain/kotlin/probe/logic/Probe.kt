package probe.logic

import kotlinx.coroutines.flow.MutableStateFlow

class Counter {
    val state = MutableStateFlow(0)
}
