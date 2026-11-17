import Fixtures
import Settings
import SwiftUI

@main
struct StarterApp: App {
    private let preferences = Fixture.launch()

    var body: some Scene {
        WindowGroup {
            NotificationSettingsView(preferences: preferences)
        }
    }
}
