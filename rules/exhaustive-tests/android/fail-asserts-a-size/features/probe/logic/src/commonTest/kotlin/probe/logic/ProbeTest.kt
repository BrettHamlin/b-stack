package probe.logic

import kotlin.test.Test
import kotlin.test.assertEquals

class ProbeTest {
    @Test
    fun counts() {
        assertEquals(2, items(listOf("a", "b", "a")).size)
    }
}
