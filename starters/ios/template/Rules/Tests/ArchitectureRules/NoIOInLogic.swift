import Foundation
import Harmonize
import Testing

/// `*Logic` modules hold state and transitions only. Side effects go through injected clients
/// (protocols in an Interface module), so tests control them. Text match on known I/O APIs.
private let ioAPIs = ["FileManager", "FileHandle", "URLSession", "UserDefaults", "contentsOf:", "NWConnection", "Process("]

@Test func noIOInLogic() {
    var hits: [String] = []
    for source in Harmonize.productionCode().sources() {
        guard let path = source.filePath?.path, path.range(of: #"/Targets/[^/]+Logic/"#, options: .regularExpression) != nil else { continue }
        for api in ioAPIs where source.source.contains(api) {
            hits.append("\(source.fileName ?? path): \(api)")
        }
    }
    #expect(hits.isEmpty, "[no-io-in-logic] I/O in a Logic module: \(hits). Call an injected client from an effect instead.")
}
