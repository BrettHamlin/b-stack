package probe.logic

// Suppress nothing: handle the null instead.
fun size(text: String?): Int = text?.length ?: 0
