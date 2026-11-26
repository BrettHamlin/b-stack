package probe.logic

/** What the board shows, worked out by the model: where the selected piece can go is a value, and whether anything
 * can move a property without parameters. */
data class ProbeState(val pieces: List<Int> = emptyList(), val selected: Int? = null, val reachable: List<Int> = emptyList()) {
    val canMove: Boolean get() = reachable.isNotEmpty()

    override fun toString(): String = "ProbeState($pieces)"
}

/** The model's own helper: top level, so the view can't import it. */
fun reachableFrom(pieces: List<Int>, from: Int): List<Int> = pieces.filter { it > from }
