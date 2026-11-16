import Fixtures
import Settings
import SwiftUI

/// The app in test mode: same features as App, composed with a fixture instead of real services.
/// Built and driven only by scripts/verify.py; never shipped.
@main
struct StarterVerifyApp: App {
    private let setup = Fixture.launch()

    var body: some Scene {
        WindowGroup {
            NotificationSettingsView(saver: setup.saver, isEnabled: setup.notificationsEnabled)
        }
    }
}
