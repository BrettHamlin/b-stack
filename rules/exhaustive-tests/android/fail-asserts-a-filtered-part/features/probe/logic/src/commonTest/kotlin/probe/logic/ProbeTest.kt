package probe.logic

import kotlin.test.Test
import kotlin.test.assertEquals

class ProbeTest {
    @Test
    fun counts() {
        assertEquals(emptyList(), items(listOf("a", "b")).filter { it.count > 1 })
    }
}
