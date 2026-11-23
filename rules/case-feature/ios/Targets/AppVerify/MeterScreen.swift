import SwiftUI
import Meter
import MeterLogic

/// AppVerify composes the rule cases' feature like any other: it builds the store from the feature's Logic and hands it
/// to the feature's view.
struct MeterScreen: View {
    private let store = MeterCounter.store()

    var body: some View { MeterView(store: store) }
}
