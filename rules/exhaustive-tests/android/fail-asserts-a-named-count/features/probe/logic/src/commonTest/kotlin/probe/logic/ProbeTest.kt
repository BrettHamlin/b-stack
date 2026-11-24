package probe.logic

import kotlin.test.Test
import kotlin.test.assertEquals

class ProbeTest {
    @Test
    fun counts() {
        assertEquals(expected = 1, actual = items(listOf("a", "b")).count { it.name == "a" })
    }
}
