import Foundation
import SwiftUI

struct RemoteCount: View {
    @State private var size = 0
    var body: some View {
        Text("\(size)").task { if let url = URL(string: "https://example.com"), let result = try? await URLSession.shared.data(from: url) { size = result.0.count } }
    }
}
