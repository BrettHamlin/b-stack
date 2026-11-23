package platform.probe

import org.junit.Assume.assumeTrue
import kotlin.test.Test
import kotlin.test.assertEquals

class ProbeTest {
    @Test
    fun onlySometimes() {
        assumeTrue(System.getenv("CI") != null)
        assertEquals(2, 1 + 1)
    }
}
