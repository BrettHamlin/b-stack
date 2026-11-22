import ComposableArchitecture
import MeterInterface
import MeterLogic
import Testing

@MainActor
@Suite struct MeterTests {
    @Test func addingCountsUp() async {
        let store = TestStore(initialState: MeterCounter.State()) { MeterCounter() }
        await store.send(.incremented) { $0.count = 1 }
        await store.send(.reset) { $0.count = 0 }
    }

    @Test func countingStopsAtTheMaximum() async {
        let store = TestStore(initialState: MeterCounter.State(count: MeterLimit.maximum)) { MeterCounter() }
        await store.send(.incremented)
    }
}
