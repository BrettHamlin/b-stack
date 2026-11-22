import ComposableArchitecture
import CaseProfileInterface
import CaseProfileLogic
import Testing

struct FixedName: NameStoring {
    func load() -> String { "Ada" }
}

@MainActor
@Suite struct ProfileTests {
    @Test func appearingShowsTheSavedName() async {
        let store = TestStore(initialState: ProfileScreen.State()) { ProfileScreen(names: FixedName()) }
        await store.send(.appeared) { $0.name = "Ada" }
    }
}
