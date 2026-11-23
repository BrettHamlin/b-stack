package platform.probe

import kotlinx.coroutines.launch

class Saver(private val save: suspend () -> Unit) {
    fun saveLater() {
        kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.SupervisorJob()).launch { save() }
    }
}
