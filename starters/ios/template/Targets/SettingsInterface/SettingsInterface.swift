import Core

public struct NotificationPreferenceError: Error, Equatable, Sendable {
    public let message: String
    public init(message: String) { self.message = message }
}

public protocol NotificationPreferenceSaving: Sendable {
    func save(enabled: Bool) async throws(NotificationPreferenceError)
}
