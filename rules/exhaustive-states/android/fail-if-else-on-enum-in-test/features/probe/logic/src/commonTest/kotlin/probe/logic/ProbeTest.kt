package probe.logic

import probe.api.Side
import kotlin.test.Test
import kotlin.test.assertEquals

class ProbeTest {
    /** The spec's model of who moves next. */
    private fun next(side: Side): Side = if (side == Side.Blue) Side.Red else Side.Blue

    @Test
    fun turnsAlternate() {
        assertEquals(listOf(Side.Red, Side.Blue), listOf(next(Side.Blue), next(Side.Red)))
    }
}
