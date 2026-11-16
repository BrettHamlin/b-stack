import Fixtures
import Settings
import SwiftUI

@main
struct StarterApp: App {
    private let setup = Fixture.launch()

    var body: some Scene {
        WindowGroup {
            NotificationSettingsView(saver: setup.saver, isEnabled: setup.notificationsEnabled)
        }
    }
}
