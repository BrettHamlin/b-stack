import Fixtures
import SwiftUI

/// The app in test mode: composed exactly like App, with a fixture's services instead of the real ones.
/// Built and driven only by scripts/verify.py; never shipped.
@main
struct StarterVerifyApp: App {
    private let fixture = Fixture.launch()

    var body: some Scene {
        WindowGroup {
            EmptyView()
        }
    }
}
