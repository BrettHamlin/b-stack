import SettingsInterface
import SwiftUI

struct ChainedTernary: View {
    let isOn: Bool
    let isSaving: Bool
    var body: some View {
        Text("T").accessibilityIdentifier(isOn ? NotificationSettingsUIID.toggle.rawValue
            : isSaving ? "raw.saving"
            : NotificationSettingsUIID.error.rawValue)
    }
}
