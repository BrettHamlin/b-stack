package probe.logic

import probe.api.Job
import probe.api.Thread

fun titles(threads: List<Thread>): List<String> = threads.map { it.title }

fun firstJob(title: String): Job = Job(title)
