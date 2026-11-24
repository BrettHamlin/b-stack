package probe.logic

import kotlin.test.Test
import kotlin.test.assertEquals

class ProbeTest {
    @Test
    fun counts() {
        assertEquals(listOf(Item("a", 2), Item("b", 1)), items(listOf("a", "b", "a")))
        assertEquals(listOf("a", "b").map { Item(it, 1) }, items(listOf("a", "b")), "expected built with map")
        assertEquals<List<Item>>(emptyList(), items(emptyList()))
        assertEquals(mapOf<String, List<Item>>("a" to listOf(Item("a", 1))), mapOf("a" to items(listOf("a"))))
        assertEquals(listOf(Item("c", 1)), items(listOf("c")).takeIf { it.size == 1 })
        assertEquals(expected = listOf(Item("d", 1)), actual = items(listOf("d")))
    }
}
