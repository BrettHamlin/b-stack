import Core
import Foundation
import Platform
public import SettingsInterface

/// Known starting states for the AppVerify build. Only AppVerify may import this module (no-fixtures-in-release),
/// so the shipped App can't be put into test mode.
///
/// AppVerify reads `BSTACK_FIXTURE` (default `standard`). `BSTACK_RESET=1` restores the fixture's starting data;
/// launching without it keeps whatever the previous run saved, which is how journeys check a relaunch.
public enum Fixture: String, CaseIterable, Sendable {
    /// Notifications on. Saves go to a UserDefaults store used only by AppVerify.
    case standard
    /// Notifications on. Every save fails with "Server unavailable".
    case saveFails = "save-fails"

    public struct Setup: Sendable {
        public let saver: any NotificationPreferenceSaving
        public let notificationsEnabled: Bool
    }

    public static func launch() -> Setup {
        launch(environment: ProcessInfo.processInfo.environment)
    }

    static func launch(environment: [String: String]) -> Setup {
        let name = environment["BSTACK_FIXTURE"] ?? Self.standard.rawValue
        guard let fixture = Fixture(rawValue: name) else {
            let known = allCases.map(\.rawValue).joined(separator: ", ")
            preconditionFailure("Unknown BSTACK_FIXTURE \"\(name)\". Known fixtures: \(known)")
        }
        return fixture.setUp(reset: environment["BSTACK_RESET"] == "1")
    }

    func setUp(reset: Bool) -> Setup {
        let preferences = StoredNotificationPreferences(suiteName: "dev.bstack.starter.verify")
        if reset {
            preferences.store(enabled: true)
        }
        switch self {
        case .standard:
            return Setup(saver: preferences, notificationsEnabled: preferences.load())
        case .saveFails:
            return Setup(saver: FailingSaver(), notificationsEnabled: preferences.load())
        }
    }
}

private struct FailingSaver: NotificationPreferenceSaving {
    func save(enabled: Bool) async throws(NotificationPreferenceError) {
        // Long enough for a journey to see the saving state before the failure arrives.
        do { try await Task.sleep(for: .milliseconds(500)) } catch { throw NotificationPreferenceError(message: "Cancelled") }
        throw NotificationPreferenceError(message: "Server unavailable")
    }
}
