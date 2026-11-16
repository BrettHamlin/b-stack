import Platform
import Settings
import SwiftUI

@main
struct StarterApp: App {
    private let preferences = StoredNotificationPreferences()

    var body: some Scene {
        WindowGroup {
            NotificationSettingsView(saver: preferences, isEnabled: preferences.load())
        }
    }
}
