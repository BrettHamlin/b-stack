import MeterInterface
import SwiftUI

struct ChainedTernary: View {
    let isOn: Bool
    let isSaving: Bool
    var body: some View {
        Text("T").accessibilityIdentifier(isOn ? MeterUIID.increment.rawValue
            : isSaving ? "raw.saving"
            : MeterUIID.reset.rawValue)
    }
}
