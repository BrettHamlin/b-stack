import MeterInterface
import SwiftUI

struct LimitLabel: View {
    var body: some View { Text("Up to \(MeterLimit.maximum)") }
}
