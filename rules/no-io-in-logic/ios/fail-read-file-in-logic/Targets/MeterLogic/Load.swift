import Foundation

func savedNote(_ path: String) throws -> String { try String(contentsOfFile: path, encoding: .utf8) }
