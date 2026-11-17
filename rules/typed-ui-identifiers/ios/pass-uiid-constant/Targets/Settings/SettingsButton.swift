import SettingsInterface
import SwiftUI

struct SettingsButton: View {
    var body: some View { Button("Settings") {}.accessibilityIdentifier(NotificationSettingsUIID.toggle.rawValue) }
}
