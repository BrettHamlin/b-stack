import Core
import MeterInterface
import SwiftUI

enum SaveStatus { case idle, saving, failed }

/// Ternaries with real conditions, module-qualified constants, and assignments (including clearing with nil).
struct StatusRow: View {
    let status: SaveStatus
    let isOn: Bool
    var body: some View {
        VStack {
            Text("A").accessibilityIdentifier(status == .failed ? MeterUIID.reset.rawValue : MeterUIID.increment.rawValue)
            Text("B").accessibilityIdentifier(isOn && status != .saving ? MeterUIID.increment.rawValue : MeterUIID.count.rawValue)
            Text("C").accessibilityIdentifier(MeterInterface.MeterUIID.increment.rawValue)
            Text("D").accessibilityIdentifier(status == .failed ? MeterUIID.reset.rawValue
                : status == .saving ? MeterUIID.count.rawValue
                : MeterUIID.increment.rawValue)
        }
    }
}

/// Stands in for a UIKit view: the rule checks assignments to any `accessibilityIdentifier`.
final class TaggedThing {
    var accessibilityIdentifier: String?

    func configure(isOn: Bool, isEnabled: Bool) {
        accessibilityIdentifier = isOn ? MeterUIID.increment.rawValue : MeterUIID.count.rawValue
        accessibilityIdentifier = isOn ? MeterUIID.increment.rawValue : isEnabled ? MeterUIID.count.rawValue : MeterUIID.reset.rawValue
        self.accessibilityIdentifier = MeterUIID.reset.rawValue
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
            Text("?").accessibilityIdentifier(maybe?.ID.rawValue ?? MeterUIID.increment.rawValue)
            Text("??").accessibilityIdentifier(maybe?.ID.rawValue ?? rows.first?.ID.rawValue ?? MeterUIID.increment.rawValue)
            Text("[]").accessibilityIdentifier(rows[0].ID.rawValue)
        }
    }
}
