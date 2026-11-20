import Core
import SettingsInterface
import SwiftUI

struct IndexedRows: View {
    let rows: [Int]

    var body: some View {
        VStack {
            ForEach(rows, id: \.self) { row in
                Text("Row").accessibilityIdentifier(NotificationSettingsUIID.toggle.at(row, 0).rawValue)
            }
        }
    }
}
