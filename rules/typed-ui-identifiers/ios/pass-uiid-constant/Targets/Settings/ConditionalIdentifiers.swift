import Core
import SettingsInterface
import SwiftUI

enum SaveStatus { case idle, saving, failed }

/// Ternaries with real conditions, module-qualified constants, and assignments (including clearing with nil).
struct StatusRow: View {
    let status: SaveStatus
    let isOn: Bool
    var body: some View {
        VStack {
            Text("A").accessibilityIdentifier(status == .failed ? NotificationSettingsUIID.error.rawValue : NotificationSettingsUIID.toggle.rawValue)
            Text("B").accessibilityIdentifier(isOn && status != .saving ? NotificationSettingsUIID.toggle.rawValue : NotificationSettingsUIID.saving.rawValue)
            Text("C").accessibilityIdentifier(SettingsInterface.NotificationSettingsUIID.toggle.rawValue)
            Text("D").accessibilityIdentifier(status == .failed ? NotificationSettingsUIID.error.rawValue
                : status == .saving ? NotificationSettingsUIID.saving.rawValue
                : NotificationSettingsUIID.toggle.rawValue)
        }
    }
}

/// Stands in for a UIKit view: the rule checks assignments to any `accessibilityIdentifier`.
final class TaggedThing {
    var accessibilityIdentifier: String?

    func configure(isOn: Bool, isEnabled: Bool) {
        accessibilityIdentifier = isOn ? NotificationSettingsUIID.toggle.rawValue : NotificationSettingsUIID.saving.rawValue
        accessibilityIdentifier = isOn ? NotificationSettingsUIID.toggle.rawValue : isEnabled ? NotificationSettingsUIID.saving.rawValue : NotificationSettingsUIID.error.rawValue
        self.accessibilityIdentifier = NotificationSettingsUIID.error.rawValue
        accessibilityIdentifier = nil
    }
}

/// Values reached from a variable are trusted whatever their property is called.
struct Tagged { let ID: UIID }

struct OddNames: View {
    let row: Tagged
    let _id: UIID
    let maybe: Tagged?
    let rows: [Tagged]
    var body: some View {
        VStack {
            Text("U").accessibilityIdentifier(row.ID.rawValue)
            Text("_").accessibilityIdentifier(_id.rawValue)
            Text("?").accessibilityIdentifier(maybe?.ID.rawValue ?? NotificationSettingsUIID.toggle.rawValue)
            Text("??").accessibilityIdentifier(maybe?.ID.rawValue ?? rows.first?.ID.rawValue ?? NotificationSettingsUIID.toggle.rawValue)
            Text("[]").accessibilityIdentifier(rows[0].ID.rawValue)
        }
    }
}
