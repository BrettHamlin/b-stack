import SwiftUI

struct AddButton: View {
    var body: some View { Button("Add") {}.accessibilityIdentifier(identifier) }
    private let identifier = "add"
}
