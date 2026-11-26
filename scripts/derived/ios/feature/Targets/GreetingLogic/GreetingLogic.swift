public import ComposableArchitecture
public import GreetingInterface

/// Greets the name typed in.
@Reducer
public struct Greeter: Sendable {
    @ObservableState
    public struct State: Equatable, Sendable {
        public var name: String
        public var shown: String

        public init(name: String = "", shown: String = "") {
            self.name = name
            self.shown = shown
        }
    }

    public enum Action: Equatable, Sendable {
        case nameChanged(String)
        case greet(PersonName)
    }

    public init() {}

    public var body: some ReducerOf<Self> {
        Reduce { state, action in
            switch action {
            case let .nameChanged(name):
                state.name = name
                return .none
            case let .greet(name):
                state.shown = "Hello, \(name.text)!"
                return .none
            }
        }
    }
}

extension Greeter {
    /// The greeting screen's store. Apps build it here and hand it to the view (views-hold-no-clients).
    @MainActor
    public static func store() -> StoreOf<Self> {
        Store(initialState: State()) { Self() }
    }
}
