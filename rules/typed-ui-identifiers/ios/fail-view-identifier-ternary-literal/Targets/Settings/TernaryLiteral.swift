import SettingsInterface
import SwiftUI

struct TernaryLiteral: View {
    let isOn: Bool
    var body: some View { Text("T").accessibilityIdentifier(isOn ? NotificationSettingsUIID.toggle.rawValue : "raw.off") }
}
