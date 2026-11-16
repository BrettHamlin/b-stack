import ComposableArchitecture
import SettingsInterface
import SettingsLogic
import Testing

/// Each save suspends on a TestClock until the test advances it, then succeeds or throws the
/// failure configured for that value. Cancellation ends the sleep, so the save never completes.
struct ControlledSaver: NotificationPreferenceSaving {
    let clock: TestClock<Duration>
    var failures: [Bool: NotificationPreferenceError] = [:]
    let calls = LockIsolated<[Bool]>([])
    let completed = LockIsolated<[Bool]>([])

    func save(enabled: Bool) async throws(NotificationPreferenceError) {
        calls.withValue { $0.append(enabled) }
        do { try await clock.sleep(for: .seconds(1)) } catch { throw NotificationPreferenceError(message: "Cancelled") }
        if let failure = failures[enabled] { throw failure }
        completed.withValue { $0.append(enabled) }
    }
}

@MainActor
private func makeStore(_ saver: ControlledSaver) -> TestStoreOf<NotificationSettings> {
    TestStore(initialState: NotificationSettings.State()) {
        NotificationSettings(saver: saver)
    }
}

@MainActor
@Suite struct NotificationSettingsTests {
    @Test func saveSucceeds() async {
        let saver = ControlledSaver(clock: TestClock())
        let store = makeStore(saver)

        await store.send(.toggleChanged(true)) {
            $0.isEnabled = true
            $0.isSaving = true
        }
        await saver.clock.advance(by: .seconds(1))
        await store.receive(\.saveSucceeded) {
            $0.isSaving = false
            $0.confirmedValue = true
        }
        #expect(saver.calls.value == [true])
        #expect(saver.completed.value == [true])
    }

    @Test func saveFailureRevertsAndShowsError() async {
        let error = NotificationPreferenceError(message: "Server unavailable")
        let saver = ControlledSaver(clock: TestClock(), failures: [true: error])
        let store = makeStore(saver)

        await store.send(.toggleChanged(true)) {
            $0.isEnabled = true
            $0.isSaving = true
        }
        await saver.clock.advance(by: .seconds(1))
        await store.receive(\.saveFailed) {
            $0.isEnabled = false
            $0.isSaving = false
            $0.errorMessage = "Server unavailable"
        }

        // The next flip clears the error.
        await store.send(.toggleChanged(true)) {
            $0.isEnabled = true
            $0.isSaving = true
            $0.errorMessage = nil
        }
        await store.send(.screenClosed) {
            $0.isSaving = false
        }
    }

    @Test func secondFlipCancelsInFlightSave() async {
        // The first save would fail; it must be cancelled so only the second (successful) result applies.
        let saver = ControlledSaver(
            clock: TestClock(),
            failures: [true: NotificationPreferenceError(message: "Stale failure")]
        )
        let store = makeStore(saver)

        await store.send(.toggleChanged(true)) {
            $0.isEnabled = true
            $0.isSaving = true
        }
        await store.send(.toggleChanged(false)) {
            $0.isEnabled = false
        }
        await saver.clock.advance(by: .seconds(1))
        await store.receive(\.saveSucceeded) {
            $0.isSaving = false
        }
        #expect(saver.calls.value == [true, false])
        #expect(saver.completed.value == [false])
    }

    @Test func closingScreenCancelsInFlightSave() async {
        let saver = ControlledSaver(clock: TestClock())
        let store = makeStore(saver)

        await store.send(.toggleChanged(true)) {
            $0.isEnabled = true
            $0.isSaving = true
        }
        await store.send(.screenClosed) {
            $0.isSaving = false
        }
        await saver.clock.advance(by: .seconds(1))
        #expect(saver.calls.value == [true])
        #expect(saver.completed.value.isEmpty)
    }
}
