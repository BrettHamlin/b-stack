import Platform
import Profile
import Settings
import SwiftUI

@main
struct StarterApp: App {
    var body: some Scene {
        WindowGroup {
            NotificationSettingsView(preferences: StoredNotificationPreferences())
            ProfileView(names: StoredName())
        }
    }
}
