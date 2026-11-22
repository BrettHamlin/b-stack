public import CaseProfileInterface
public import ComposableArchitecture

@Reducer
public struct ProfileScreen: Sendable {
    @ObservableState
    public struct State: Equatable, Sendable {
        public var name: String

        public init(name: String = "") {
            self.name = name
        }
    }

    public enum Action: Equatable, Sendable {
        case appeared
    }

    let names: any NameStoring

    public init(names: any NameStoring) {
        self.names = names
    }

    public var body: some ReducerOf<Self> {
        Reduce { state, action in
            switch action {
            case .appeared:
                state.name = names.load()
                return .none
            }
        }
    }
}
