import MeterInterface
import SwiftUI

struct TernaryLiteral: View {
    let isOn: Bool
    var body: some View { Text("T").accessibilityIdentifier(isOn ? MeterUIID.increment.rawValue : "raw.off") }
}
