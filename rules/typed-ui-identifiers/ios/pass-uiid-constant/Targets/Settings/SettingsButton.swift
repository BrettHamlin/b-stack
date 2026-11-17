import Core
import SettingsInterface
import SwiftUI

struct SettingsButton: View {
    var body: some View { Button("Settings") {}.accessibilityIdentifier(NotificationSettingsUIID.toggle.rawValue) }
}

/// A reusable row tagged with whatever identifier its caller passes in.
struct TaggedRow: View {
    let id: UIID
    let isSaving: Bool
    var body: some View {
        VStack {
            Text("Row").accessibilityIdentifier(id.rawValue)
            Text("Self").accessibilityIdentifier(self.id.rawValue)
            Text("State").accessibilityIdentifier(isSaving ? NotificationSettingsUIID.saving.rawValue : NotificationSettingsUIID.toggle.rawValue)
        }
    }
}

struct Model { let id: UIID }

struct ModelRow: View {
    let row: Model
    var body: some View { Text("Model").accessibilityIdentifier(row.id.rawValue) }
}
