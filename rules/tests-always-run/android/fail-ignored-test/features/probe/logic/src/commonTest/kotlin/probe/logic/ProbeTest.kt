package probe.logic

import kotlin.test.Ignore
import kotlin.test.Test
import kotlin.test.assertEquals

class ProbeTest {
    @Ignore
    @Test
    fun flaky() {
        assertEquals(2, 1 + 1)
    }
}
