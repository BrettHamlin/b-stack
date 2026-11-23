import Core
import SettingsInterface
public import SettingsLogic
public import ComposableArchitecture
public import SwiftUI

/// The notification settings screen. It gets only its store, built by `NotificationSettings.store(preferences:)` in
/// SettingsLogic, so it can show state and send actions but never reach the preferences client itself.
public struct NotificationSettingsView: View {
    @Bindable var store: StoreOf<NotificationSettings>

    public init(store: StoreOf<NotificationSettings>) {
        self.store = store
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
