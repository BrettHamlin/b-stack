import SwiftUI

struct RememberedCount: View {
    @AppStorage("meterCount") private var count = 0
    var body: some View { Text("\(count)") }
}
