package probe.logic

sealed interface Outcome {
    val retryable: Boolean
    val retryAfterMs: Long
    val kind: Kind
    val mask: Int
    val title: String
    val mark: Char
}
