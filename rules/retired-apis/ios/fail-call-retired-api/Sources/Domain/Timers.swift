public enum TaskScope {
    public static func run(_ work: @escaping @Sendable () async -> Void) {}
}
@available(*, unavailable, message: "Use TaskScope.run, which cancels when the feature ends")
public func legacyTimer(_ work: @escaping @Sendable () -> Void) {}
