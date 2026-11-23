package probe.api

import kotlin.jvm.JvmInline

@JvmInline
value class ThreadId(val value: Int)

data class Thread(val id: ThreadId, val title: String)

data class Job(val title: String)
