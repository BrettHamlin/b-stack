import SwiftUI

struct Warmup: View {
    var body: some View { Text("Ready").task { await Task.yield() } }
}
