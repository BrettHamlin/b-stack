public import ComposableArchitecture
import MeterInterface

/// Counts taps, up to MeterLimit.maximum.
@Reducer
public struct MeterCounter: Sendable {
    @ObservableState
    public struct State: Equatable, Sendable {
        public var count: Int

        public init(count: Int = 0) {
            self.count = count
        }
    }

    public enum Action: Equatable, Sendable {
        case incremented
        case reset
    }

    public init() {}

    public var body: some ReducerOf<Self> {
        Reduce { state, action in
            switch action {
            case .incremented:
                state.count = min(state.count + 1, MeterLimit.maximum)
                return .none
            case .reset:
                state.count = 0
                return .none
            }
        }
    }
}

extension MeterCounter {
    /// The meter screen's store. Apps build it here and hand it to the view (views-hold-no-clients).
    @MainActor
    public static func store() -> StoreOf<Self> {
        Store(initialState: State()) { Self() }
    }
}
