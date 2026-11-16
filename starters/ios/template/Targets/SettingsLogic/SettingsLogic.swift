import Core
public import SettingsInterface
public import ComposableArchitecture

@Reducer
public struct NotificationSettings: Sendable {
    @ObservableState
    public struct State: Equatable, Sendable {
        public var isEnabled: Bool
        public var isSaving: Bool
        public var errorMessage: String?
        /// The last value known to be persisted; a failed save reverts the toggle to it.
        public var confirmedValue: Bool

        public init(isEnabled: Bool = false, isSaving: Bool = false, errorMessage: String? = nil) {
            self.isEnabled = isEnabled
            self.isSaving = isSaving
            self.errorMessage = errorMessage
            self.confirmedValue = isEnabled
        }
    }

    public enum Action: Equatable, Sendable {
        case toggleChanged(Bool)
        case saveSucceeded(Bool)
        case saveFailed(NotificationPreferenceError)
        case screenClosed
    }

    enum CancelID { case save }

    // Injected through init rather than `@Dependency`: this project links TCA statically into each module, so a
    // `withDependencies` override made from another module would set a different task-local than the one read here.
    let saver: any NotificationPreferenceSaving

    public init(saver: any NotificationPreferenceSaving) {
        self.saver = saver
    }

    public var body: some ReducerOf<Self> {
        Reduce { state, action in
            switch action {
            case let .toggleChanged(isEnabled):
                state.isEnabled = isEnabled
                state.isSaving = true
                state.errorMessage = nil
                return .run { [saver] send in
                    do throws(NotificationPreferenceError) {
                        try await saver.save(enabled: isEnabled)
                        await send(.saveSucceeded(isEnabled))
                    } catch {
                        await send(.saveFailed(error))
                    }
                }
                .cancellable(id: CancelID.save, cancelInFlight: true)

            case let .saveSucceeded(value):
                state.isSaving = false
                state.confirmedValue = value
                return .none

            case let .saveFailed(error):
                state.isEnabled = state.confirmedValue
                state.isSaving = false
                state.errorMessage = error.message
                return .none

            case .screenClosed:
                state.isSaving = false
                return .cancel(id: CancelID.save)
            }
        }
    }
}
