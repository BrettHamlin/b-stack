import Foundation

/// Known starting states for the AppVerify build. Only AppVerify may import this module (no-fixtures-in-release),
/// so the shipped App can't be put into test mode. AppVerify reads `BSTACK_FIXTURE` (default `standard`).
public enum Fixture: String, CaseIterable, Sendable {
    /// The app as a new user first opens it.
    case standard

    public static func launch() -> Fixture {
        let name = ProcessInfo.processInfo.environment["BSTACK_FIXTURE"] ?? Self.standard.rawValue
        guard let fixture = Fixture(rawValue: name) else {
            let known = allCases.map(\.rawValue).joined(separator: ", ")
            preconditionFailure("Unknown BSTACK_FIXTURE \"\(name)\". Known fixtures: \(known)")
        }
        return fixture
    }
}
