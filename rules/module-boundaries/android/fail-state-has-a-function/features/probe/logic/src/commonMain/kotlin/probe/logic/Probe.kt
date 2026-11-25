package probe.logic

/** What the board shows: the view would work out where a piece can go by calling reachable(). */
data class ProbeState(val pieces: List<Int> = emptyList()) {
    fun reachable(from: Int): List<Int> = pieces.filter { it > from }
}
