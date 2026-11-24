package probe.logic

import kotlin.test.Test
import kotlin.test.assertEquals

class ProbeTest {
    @Test
    fun counts() {
        assertEquals(true, items(listOf("a")).any { it.count == 1 }, "one a")
    }
}
