import SwiftUI
enum UIID { static let settings = "settings" }
struct SettingsButton: View {
    var body: some View { Button("Settings") {}.accessibilityIdentifier(UIID.settings) }
}
