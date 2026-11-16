import Core
public import SettingsInterface
public import SettingsLogic
public import ComposableArchitecture
public import SwiftUI

public struct NotificationSettingsView: View {
    @Bindable var store: StoreOf<NotificationSettings>

    public init(store: StoreOf<NotificationSettings>) {
        self.store = store
    }

    public init(saver: any NotificationPreferenceSaving, isEnabled: Bool) {
        self.init(
            store: Store(initialState: NotificationSettings.State(isEnabled: isEnabled)) {
                NotificationSettings(saver: saver)
            }
        )
    }

    public var body: some View {
        Form {
            Toggle("Notifications", isOn: $store.isEnabled.sending(\.toggleChanged))
                .accessibilityIdentifier(NotificationSettingsUIID.toggle)
            if store.isSaving {
                ProgressView("Saving…")
                    .accessibilityIdentifier(NotificationSettingsUIID.saving)
            }
            if let message = store.errorMessage {
                Text(message)
                    .foregroundStyle(.red)
                    .accessibilityIdentifier(NotificationSettingsUIID.error)
            }
        }
        .onDisappear { store.send(.screenClosed) }
    }
}
