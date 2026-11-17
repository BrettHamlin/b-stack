import Core
import SwiftUI

struct SettingsButton: View {
    let id: UIID?
    var body: some View { Button("Settings") {}.accessibilityIdentifier(id?.rawValue ?? "settings") }
}
