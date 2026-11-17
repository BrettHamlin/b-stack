import struct Fixtures.Fixture
import Platform
import Settings
import SwiftUI

@main
struct StarterApp: App {
    var body: some Scene {
        WindowGroup {
            NotificationSettingsView(preferences: StoredNotificationPreferences())
        }
    }
}
