import Core
import MeterInterface
import SwiftUI

struct IndexedRows: View {
    let rows: [Int]

    var body: some View {
        VStack {
            ForEach(rows, id: \.self) { row in
                Text("Row").accessibilityIdentifier(MeterUIID.increment.at(row, 0).rawValue)
            }
        }
    }
}
