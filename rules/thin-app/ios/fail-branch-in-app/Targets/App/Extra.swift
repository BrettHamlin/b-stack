import SwiftUI

struct Welcome: View {
    let firstLaunch: Bool
    var body: some View {
        if firstLaunch { Text("Welcome") } else { Text("Hello again") }
    }
}
