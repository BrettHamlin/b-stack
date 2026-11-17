import SwiftUI

struct SettingsButton: View {
    var body: some View {
        VStack {
            Button("Settings") {}.accessibilityIdentifier( "settings")
            Button("More") {}.accessibilityIdentifier("more" as String)
        }
    }
}
