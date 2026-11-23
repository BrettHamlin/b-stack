package probe.logic

enum class Kind { Main, Retry }

data object Done : Outcome {
    override val retryable = false
    override val retryAfterMs: Long = 30_000L
    override val kind = Kind.Main
    override val mask = 0xFF
    /** Shown as `${title}` in the list. */
    override val title get() = "Done"
    override val mark = '\u00B7'
}
