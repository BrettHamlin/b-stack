final class Counter { var count = 0 }
func bump(_ counter: Counter) async { await Task.detached { counter.count += 1 }.value }
