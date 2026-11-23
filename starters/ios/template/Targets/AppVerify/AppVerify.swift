import Fixtures
import Settings
import SettingsLogic
import SwiftUI

/// The app in test mode: composed exactly like App, with a fixture's preferences instead of the real ones.
/// Built and driven only by scripts/verify.py; never shipped.
@main
struct StarterVerifyApp: App {
    private let settings = NotificationSettings.store(preferences: Fixture.launch())

    var body: some Scene {
        WindowGroup {
            NotificationSettingsView(store: settings)
        }
    }
}
