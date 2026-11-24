package probe.api

sealed interface Phase {
    data object Idle : Phase

    data object Running : Phase

    data class Done(val score: Int) : Phase
}

enum class Mode { Easy, Hard }
