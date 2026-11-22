import ComposableArchitecture
import MeterLogic
import Testing

@MainActor
@Test func relaxedStore() async {
    let store = TestStore(initialState: MeterCounter.State()) { MeterCounter() }
    store.exhaustivity = .off
}
