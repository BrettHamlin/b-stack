import Foundation

func storedPreference() -> Data? { FileManager.default.contents(atPath: "/tmp/preference") }
