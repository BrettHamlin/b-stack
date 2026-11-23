package probe.logic

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf

fun numbers(): Flow<Int> = flowOf(1, 2, 3)
