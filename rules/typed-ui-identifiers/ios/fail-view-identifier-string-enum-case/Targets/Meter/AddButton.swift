import SwiftUI

enum IDs: String { case addUIID = "add" }

struct AddButton: View {
    var body: some View { Button("Add") {}.accessibilityIdentifier(IDs.addUIID.rawValue) }
}
