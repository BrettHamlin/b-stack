import ComposableArchitecture
import SettingsInterface
import SettingsLogic
import Testing

/// Property test: random sequences of user steps, each checked against a model of the feature's spec by an
/// exhaustive TestStore. It catches orderings the example tests don't spell out (e.g. a failed save of the value
/// that is already saved). The model is written from the spec, never from the reducer, and builds its own starting
/// state: sharing code with the reducer would let a bug in that code pass both.

/// Deterministic random numbers, so a failing sequence replays from the same seed.
private struct SplitMix64: RandomNumberGenerator {
    var state: UInt64
    mutating func next() -> UInt64 {
        state &+= 0x9E37_79B9_7F4A_7C15
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58_476D_1CE4_E5B9
        z = (z ^ (z >> 27)) &* 0x94D0_49BB_1331_11EB
        return z ^ (z >> 31)
    }
}

private enum Step: CustomStringConvertible {
    case toggle(Bool)
    case wait
    case close

    var description: String {
        switch self {
        case let .toggle(value): "toggle(\(value))"
        case .wait: "wait(0.5s)"
        case .close: "close"
        }
    }
}

/// The spec:
/// - The screen starts showing the saved value, not saving, with no error.
/// - Flipping the toggle shows the new value, clears any error, and starts a 1 s save that replaces any save in flight.
/// - A save that succeeds becomes the saved value. A save that fails puts the toggle back to the saved value and
///   shows the error.
/// - Closing the screen stops any save in flight.
private struct Model {
    var state: NotificationSettings.State
    var now: Duration = .zero
    var pending: (value: Bool, due: Duration)?
    var calls: [Bool] = []
    var completed: [Bool] = []

    enum Completion { case succeeded(Bool), failed(NotificationPreferenceError) }

    init(saved: Bool) {
        var state = NotificationSettings.State()
        state.isEnabled = saved
        state.isSaving = false
        state.errorMessage = nil
        state.confirmedValue = saved
        self.state = state
    }

    mutating func toggle(_ value: Bool) {
        state.isEnabled = value
        state.isSaving = true
        state.errorMessage = nil
        pending = (value, now + .seconds(1))
        calls.append(value)
    }

    mutating func close() {
        state.isSaving = false
        pending = nil
    }

    /// Advances half a second; returns the save that finished, if one did.
    mutating func wait(failures: [Bool: NotificationPreferenceError]) -> Completion? {
        now += .milliseconds(500)
        guard let save = pending, save.due <= now else { return nil }
        pending = nil
        state.isSaving = false
        if let error = failures[save.value] {
            state.isEnabled = state.confirmedValue
            state.errorMessage = error.message
            return .failed(error)
        }
        state.confirmedValue = save.value
        completed.append(save.value)
        return .succeeded(save.value)
    }
}

@MainActor
@Suite struct NotificationSettingsPropertyTests {
    @Test func randomSequencesMatchTheSpec() async {
        var rng = SplitMix64(state: 20_261_117)
        for sequence in 0..<200 {
            let saved = Bool.random(using: &rng)
            var failures: [Bool: NotificationPreferenceError] = [:]
            if Bool.random(using: &rng) { failures[true] = NotificationPreferenceError(message: "Could not save on") }
            if Bool.random(using: &rng) { failures[false] = NotificationPreferenceError(message: "Could not save off") }
            let steps = (0..<Int.random(in: 1...12, using: &rng)).map { _ -> Step in
                let roll = Int.random(in: 0..<10, using: &rng)
                if roll < 4 { return .toggle(Bool.random(using: &rng)) }
                return roll < 9 ? .wait : .close
            }
            let failing = failures.keys.map { $0 ? "on" : "off" }.sorted()
            let replay = "sequence \(sequence): saved \(saved), failing saves \(failing), steps \(steps)"
            // Stop at the first sequence that diverges: once one does, the rest only repeat it (and each waits out
            // TestStore's timeouts).
            guard await matchesSpec(saved: saved, failures: failures, steps: steps, replay: replay) else { return }
        }
    }

    private func matchesSpec(
        saved: Bool, failures: [Bool: NotificationPreferenceError], steps: [Step], replay: String
    ) async -> Bool {
        let saver = ControlledSaver(clock: TestClock(), failures: failures)
        var model = Model(saved: saved)
        let store = TestStore(initialState: NotificationSettings.State(isEnabled: saved)) {
            NotificationSettings(saver: saver)
        }
        guard store.state == model.state else {
            Issue.record("Starting state differs from the spec. \(replay)")
            return false
        }
        for (index, step) in (steps + [.close]).enumerated() {
            let before = model.state
            switch step {
            case let .toggle(value):
                model.toggle(value)
                await send(store, .toggleChanged(value), changed: before != model.state, to: model.state)
            case .close:
                model.close()
                await send(store, .screenClosed, changed: before != model.state, to: model.state)
            case .wait:
                let completion = model.wait(failures: failures)
                await saver.clock.advance(by: .milliseconds(500))
                switch completion {
                case .none:
                    break
                case let .succeeded(value):
                    await store.receive(.saveSucceeded(value)) { [expected = model.state] in $0 = expected }
                case let .failed(error):
                    await store.receive(.saveFailed(error)) { [expected = model.state] in $0 = expected }
                }
            }
            guard store.state == model.state else {
                Issue.record("Diverged from the spec at step \(index) (\(step)). \(replay)")
                return false
            }
        }
        await store.finish()
        guard saver.calls.value == model.calls, saver.completed.value == model.completed else {
            Issue.record("Saves differ from the spec: \(saver.calls.value) started, \(saver.completed.value) completed. \(replay)")
            return false
        }
        return true
    }

    /// TestStore rejects an assertion closure when the state doesn't change, so pass one only when it does.
    private func send(
        _ store: TestStoreOf<NotificationSettings>,
        _ action: NotificationSettings.Action,
        changed: Bool,
        to expected: NotificationSettings.State
    ) async {
        if changed {
            await store.send(action) { $0 = expected }
        } else {
            await store.send(action)
        }
    }
}
