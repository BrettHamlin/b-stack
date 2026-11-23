package probe.logic

import kotlinx.coroutines.DelicateCoroutinesApi
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch

@OptIn(DelicateCoroutinesApi::class)
fun fireAndForget(work: suspend () -> Unit) {
    GlobalScope.launch { work() }
}
