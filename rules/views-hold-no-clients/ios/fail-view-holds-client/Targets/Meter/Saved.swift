import MeterInterface
import SwiftUI

struct SavedCount: View {
    let source: any MeterStore
    var body: some View { Text("\(source.load())") }
}
