import ComposableArchitecture
import SettingsInterface
import SettingsLogic
import Testing

private struct NoopSaver: NotificationPreferenceSaving {
    func save(enabled: Bool) async throws(NotificationPreferenceError) {}
}

@MainActor
@Test func relaxedStore() async {
    let store = TestStore(initialState: NotificationSettings.State()) { NotificationSettings(saver: NoopSaver()) }
    store.exhaustivity = .off
}
