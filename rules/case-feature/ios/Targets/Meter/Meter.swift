import Core
import MeterInterface
public import MeterLogic
public import ComposableArchitecture
public import SwiftUI

public struct MeterView: View {
    let store: StoreOf<MeterCounter>
    private let incrementID: UIID = MeterUIID.increment

    public init() {
        store = Store(initialState: MeterCounter.State()) { MeterCounter() }
    }

    public var body: some View {
        VStack {
            Text("\(store.count)")
                .accessibilityIdentifier(MeterUIID.count.rawValue)
            Button("Add") { store.send(.incremented) }
                .accessibilityIdentifier(incrementID.rawValue)
            Button("Reset") { store.send(.reset) }
                .accessibilityIdentifier(MeterUIID.reset.rawValue)
        }
    }
}
