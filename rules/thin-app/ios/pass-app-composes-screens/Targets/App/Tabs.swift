import Meter
import MeterLogic
import SwiftUI

struct Tabs: View {
    private let meter = MeterCounter.store()

    var body: some View {
        TabView {
            MeterView(store: meter)
            Text("About")
        }
    }
}
