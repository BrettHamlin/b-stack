final class SessionStore {
    static let shared = SessionStore()
    var userName = ""
}
func greeting() -> String { "Hi \(SessionStore.shared.userName)" }
