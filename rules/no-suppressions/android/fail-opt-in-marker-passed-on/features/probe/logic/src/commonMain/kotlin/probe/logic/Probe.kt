package probe.logic

import kotlinx.coroutines.ExperimentalCoroutinesApi

@ExperimentalCoroutinesApi
fun hurry(work: () -> Unit) = work()
