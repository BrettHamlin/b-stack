import Core
public import SettingsInterface

public actor FakeNotificationPreferenceSaver: NotificationPreferenceSaving {
    public private(set) var savedValues: [Bool] = []
    private let delay: Duration
    private let failure: NotificationPreferenceError?

    public init(delay: Duration = .milliseconds(300), failure: NotificationPreferenceError? = nil) {
        self.delay = delay
        self.failure = failure
    }

    public func save(enabled: Bool) async throws(NotificationPreferenceError) {
        do { try await Task.sleep(for: delay) } catch { throw NotificationPreferenceError(message: "Cancelled") }
        if let failure { throw failure }
        savedValues.append(enabled)
    }
}
