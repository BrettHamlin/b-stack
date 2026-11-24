package probe.logic

import kotlin.test.Test
import kotlin.test.assertEquals

class ProbeTest {
    @Test
    fun sums() = checkSum(listOf(1, 2), 3)

    private fun checkSum(values: List<Int>, expected: Int) {
        assertEquals(expected, values.sum())
    }
}
