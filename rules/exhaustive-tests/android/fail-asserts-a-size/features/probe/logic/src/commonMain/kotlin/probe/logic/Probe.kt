package probe.logic

data class Item(val name: String, val count: Int)

fun items(names: List<String>): List<Item> = names.groupingBy { it }.eachCount().map { (name, count) -> Item(name, count) }
