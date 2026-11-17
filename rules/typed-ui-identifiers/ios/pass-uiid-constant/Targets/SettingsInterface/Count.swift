/// Ordinary value types in an Interface module may construct themselves with Self(...).
public struct Count: Sendable {
    public let value: Int

    public init(_ value: Int) {
        self.value = value
    }

    public static func + (lhs: Count, rhs: Count) -> Count {
        Self(lhs.value + rhs.value)
    }
}
