package probe.logic

import probe.api.Hex

/** Rules live in logic: the hexes beside [hex]. */
fun neighbors(hex: Hex): List<Hex> =
    listOf(Hex(hex.col + 1, hex.row), Hex(hex.col - 1, hex.row), Hex(hex.col, hex.row + 1), Hex(hex.col, hex.row - 1))
