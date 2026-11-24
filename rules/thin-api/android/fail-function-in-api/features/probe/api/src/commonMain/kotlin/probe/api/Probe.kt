package probe.api

data class Hex(val col: Int, val row: Int) {
    fun neighbors(): List<Hex> = listOf(Hex(col + 1, row), Hex(col - 1, row), Hex(col, row + 1), Hex(col, row - 1))
}
