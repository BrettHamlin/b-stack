package probe.logic

import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class Saver(private val scope: CoroutineScope, private val io: CoroutineDispatcher, private val save: suspend () -> Unit) {
    fun saveLater() {
        scope.launch { withContext(io) { save() } }
    }
}
