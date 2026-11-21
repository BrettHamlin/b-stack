import Core
import SwiftUI

struct AddButton: View {
    let id: UIID?
    var body: some View { Button("Add") {}.accessibilityIdentifier(id?.rawValue ?? "add") }
}
