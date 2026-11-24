package probe.logic

import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch

fun fireAndForget(work: suspend () -> Unit) {
    GlobalScope.launch { work() }
}
