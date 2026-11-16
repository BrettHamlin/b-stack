import ComposableArchitecture
import SettingsInterface
import SettingsLogic
import Testing

private struct NoopSaver: NotificationPreferenceSaving {
    func save(enabled: Bool) async throws(NotificationPreferenceError) {}
}

@MainActor
@Test func closingWithoutSaveChangesNothing() async {
    let store = TestStore(initialState: NotificationSettings.State()) { NotificationSettings(saver: NoopSaver()) }
    await store.send(.screenClosed)
}
