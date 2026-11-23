// Loaded by URLSession in Platform, never here.
func merged(_ first: [Int], _ second: [Int]) -> [Int] {
    var all = first
    all.append(contentsOf: second)
    return all
}

let storageNote = "UserDefaults lives in Platform"
