import SwiftUI

struct SettingsButton: View {
    var body: some View { Button("Settings") {}.accessibilityIdentifier(identifier) }
    private let identifier = "settings"
}
