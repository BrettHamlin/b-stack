public import Core

public protocol NameStoring: Sendable {
    func load() -> String
}

public enum ProfileUIID {
    public static let name = UIID("profile.name")
}
