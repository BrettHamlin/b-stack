public import Core

/// A name to greet, as typed.
public struct PersonName: Equatable, Sendable {
    public let text: String

    public init(_ text: String) {
        self.text = text
    }
}

/// Accessibility identifiers for the greeting screen.
public enum GreeterUIID {
    public static let name = UIID("greeter.name")
    public static let greet = UIID("greeter.greet")
    public static let shown = UIID("greeter.shown")
}
