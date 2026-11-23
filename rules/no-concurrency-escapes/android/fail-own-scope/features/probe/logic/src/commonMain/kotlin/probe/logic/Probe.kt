package probe.logic

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class Saver(private val save: suspend () -> Unit) {
    fun saveLater() {
        CoroutineScope(SupervisorJob()).launch { save() }
    }
}
