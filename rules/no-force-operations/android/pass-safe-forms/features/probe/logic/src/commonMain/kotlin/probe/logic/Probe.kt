package probe.logic

fun size(text: String?): Int = text?.length ?: 0

fun count(value: Any): Int = (value as? Int) ?: 0

fun top(scores: List<Int>): Int? = scores.firstOrNull()

fun score(scores: Map<String, Int>): Int = scores["ada"] ?: 0

fun guarded(work: () -> Int): Int = try {
    work()
} catch (stop: IllegalStateException) {
    throw stop
}
