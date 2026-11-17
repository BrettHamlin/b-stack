import Core
import SettingsInterface
import SwiftUI

struct SettingsButton: View {
    var body: some View { Button("Settings") {}.accessibilityIdentifier(NotificationSettingsUIID.toggle.rawValue) }
}

/// A reusable row tagged with whatever identifier its caller passes in.
struct TaggedRow: View {
    let id: UIID
    var body: some View { Text("Row").accessibilityIdentifier(id.rawValue) }
}
