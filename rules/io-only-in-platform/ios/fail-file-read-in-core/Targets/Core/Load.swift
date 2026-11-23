import Foundation

func loadBlob(_ url: URL) throws -> Data { try Data(contentsOf: url) }
func saveBlob(_ blob: Data, to url: URL) throws { try blob.write(to: url) }
