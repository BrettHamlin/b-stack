import Foundation
public import ProfileInterface

public struct StoredName: NameStoring {
    public init() {}

    public func load() -> String {
        UserDefaults.standard.string(forKey: "profileName") ?? ""
    }
}
