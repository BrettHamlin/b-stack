package probe.logic

import kotlin.test.Test
import kotlin.test.assertEquals

class ProbeTest {
    @Test
    fun sizes() {
        assertEquals(3, size("abc"))
        assertEquals(0, size(null))
        assertEquals(listOf(1, 2), listOf(1, 2).takeIf { it.isNotEmpty() } ?: error("tests may throw"))
    }
}
