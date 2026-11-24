package probe.logic

import kotlin.test.Test
import kotlin.test.assertEquals

class ProbeTest {
    @Test
    fun counts() {
        assertEquals(listOf("a", "b"), items(listOf("a", "b", "a")).map { it.name })
    }
}
