import Fixtures
import Profile
import Settings
import SwiftUI

@main
struct StarterVerifyApp: App {
    private let preferences = Fixture.launch()

    var body: some Scene {
        WindowGroup {
            NotificationSettingsView(preferences: preferences)
            ProfileView(names: FixtureName())
        }
    }
}
