import Foundation
public import CaseProfileInterface

public struct StoredName: NameStoring {
    public init() {}

    public func load() -> String {
        UserDefaults.standard.string(forKey: "profileName") ?? ""
    }
}
