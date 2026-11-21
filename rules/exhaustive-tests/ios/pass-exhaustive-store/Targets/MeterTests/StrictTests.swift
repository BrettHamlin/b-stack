import ComposableArchitecture
import MeterLogic
import Testing

@MainActor
@Test func resettingAtZeroChangesNothing() async {
    let store = TestStore(initialState: MeterCounter.State()) { MeterCounter() }
    await store.send(.reset)
}
