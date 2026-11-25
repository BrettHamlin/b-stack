import ComposableArchitecture
import GreetingInterface
import GreetingLogic
import Testing

@MainActor
@Suite struct GreetingTests {
    @Test func greetsTheNameTypedIn() async {
        let store = TestStore(initialState: Greeter.State()) { Greeter() }
        await store.send(.nameChanged("Ada")) { $0.name = "Ada" }
        await store.send(.greet(PersonName("Ada"))) { $0.shown = "Hello, Ada!" }
    }
}
