package probe.api

data class Hex(val col: Int, val row: Int) {
    val isEdge: Boolean
        get() = col == 0 || row == 0
}
