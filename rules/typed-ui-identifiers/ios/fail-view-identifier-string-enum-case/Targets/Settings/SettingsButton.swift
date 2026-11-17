import SwiftUI

enum IDs: String { case settingsUIID = "settings" }

struct SettingsButton: View {
    var body: some View { Button("Settings") {}.accessibilityIdentifier(IDs.settingsUIID.rawValue) }
}
