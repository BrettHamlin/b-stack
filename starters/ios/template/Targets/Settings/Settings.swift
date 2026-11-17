import Core
public import SettingsInterface
public import SettingsLogic
public import ComposableArchitecture
public import SwiftUI

public struct NotificationSettingsView: View {
    @Bindable var store: StoreOf<NotificationSettings>

    /// Internal: apps compose the screen through init(preferences:), which loads the saved value.
    init(store: StoreOf<NotificationSettings>) {
        self.store = store
    }

    /// The screen as both apps compose it: it starts from the saved value and saves changes to the same place.
    public init(preferences: any NotificationPreferences) {
        self.init(
            store: Store(initialState: NotificationSettings.State(isEnabled: preferences.load())) {
                NotificationSettings(saver: preferences)
            }
        )
    }

    public var body: some View {
        Form {
            Toggle("Notifications", isOn: $store.isEnabled.sending(\.toggleChanged))
                .accessibilityIdentifier(NotificationSettingsUIID.toggle.rawValue)
            if store.isSaving {
                ProgressView("Saving…")
                    .accessibilityIdentifier(NotificationSettingsUIID.saving.rawValue)
            }
            if let message = store.errorMessage {
                Text(message)
                    .foregroundStyle(.red)
                    .accessibilityIdentifier(NotificationSettingsUIID.error.rawValue)
            }
        }
        .onDisappear { store.send(.screenClosed) }
    }
}
