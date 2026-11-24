package probe.logic

class Totals {
    var lastTotal: Int = 0
        private set

    fun add(values: List<Int>): Int {
        val sum = Sum()
        values.forEach { sum.total += it }
        lastTotal = sum.total
        return lastTotal
    }

    private class Sum {
        var total = 0
    }
}
