import Core
import MeterInterface
import SwiftUI

struct AddButton: View {
    var body: some View { Button("Add") {}.accessibilityIdentifier(MeterUIID.increment.rawValue) }
}

/// A reusable row tagged with whatever identifier its caller passes in.
struct TaggedRow: View {
    let id: UIID
    let isSaving: Bool
    var body: some View {
        VStack {
            Text("Row").accessibilityIdentifier(id.rawValue)
            Text("Self").accessibilityIdentifier(self.id.rawValue)
            Text("State").accessibilityIdentifier(isSaving ? MeterUIID.count.rawValue : MeterUIID.increment.rawValue)
        }
    }
}

struct Model { let id: UIID }

struct ModelRow: View {
    let row: Model
    var body: some View { Text("Model").accessibilityIdentifier(row.id.rawValue) }
}
