import Platform
import Settings
import SettingsLogic
import SwiftUI

@main
struct StarterApp: App {
    private let settings = NotificationSettings.store(preferences: StoredNotificationPreferences())

    var body: some Scene {
        WindowGroup {
            NotificationSettingsView(store: settings)
        }
    }
}
