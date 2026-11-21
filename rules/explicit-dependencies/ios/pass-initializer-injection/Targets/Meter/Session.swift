final class SessionStore { var userName = "" }
struct Greeter {
    let session: SessionStore
    func greeting() -> String { "Hi \(session.userName)" }
}
