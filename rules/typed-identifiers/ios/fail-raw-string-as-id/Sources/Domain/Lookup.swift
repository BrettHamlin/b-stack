public struct UserID: Hashable, Sendable {
    public let raw: String
    public init(_ raw: String) { self.raw = raw }
}
func find(_ id: UserID) {}
func lookup() { find("abc") }
