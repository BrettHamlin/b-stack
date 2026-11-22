import Foundation

func cachedPreference() -> Data? { FileManager.default.contents(atPath: "/tmp/preference") }
