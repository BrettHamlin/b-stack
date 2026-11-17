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
    /// Notifications on. Saves are stored, in AppVerify's own UserDefaults.
    case standard
    /// Notifications on. Every save fails with "Server unavailable".
    case saveFails = "save-fails"

    public static func launch() -> any NotificationPreferences {
        launch(environment: ProcessInfo.processInfo.environment)
    }

    static func launch(environment: [String: String]) -> any NotificationPreferences {
        let name = environment["BSTACK_FIXTURE"] ?? Self.standard.rawValue
        guard let fixture = Fixture(rawValue: name) else {
            let known = allCases.map(\.rawValue).joined(separator: ", ")
            preconditionFailure("Unknown BSTACK_FIXTURE \"\(name)\". Known fixtures: \(known)")
        }
        return fixture.setUp(reset: environment["BSTACK_RESET"] == "1")
    }

    func setUp(reset: Bool) -> any NotificationPreferences {
        let preferences = StoredNotificationPreferences()
        if reset {
            preferences.store(enabled: true)
        }
        switch self {
        case .standard:
            return preferences
        case .saveFails:
            return FailingPreferences(stored: preferences)
        }
    }
}

/// Loads the stored value, but every save fails.
private struct FailingPreferences: NotificationPreferences {
    let stored: StoredNotificationPreferences

    func load() -> Bool {
        stored.load()
    }

    func save(enabled: Bool) async throws(NotificationPreferenceError) {
        // Long enough for a journey to see the saving state before the failure arrives.
        do { try await Task.sleep(for: .milliseconds(500)) } catch { throw NotificationPreferenceError(message: "Cancelled") }
        throw NotificationPreferenceError(message: "Server unavailable")
    }
}
