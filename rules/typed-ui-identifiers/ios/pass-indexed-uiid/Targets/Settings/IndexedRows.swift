import Core
import SettingsInterface
import SwiftUI

struct IndexedRows: View {
    let rows: [Int]
    let id: UIID

    var body: some View {
        VStack {
            ForEach(rows, id: \.self) { row in
                Text("Row").accessibilityIdentifier(NotificationSettingsUIID.toggle.at(row, 0).rawValue)
                Text("Cell").accessibilityIdentifier(id.at(row).rawValue)
            }
        }
    }
}
