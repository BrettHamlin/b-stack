import Fixtures
import CaseProfile
import SwiftUI

/// The test-mode app composes it the same way, with a fixture's storage.
struct CaseProfileScreen: View {
    var body: some View { ProfileView(names: FixtureName()) }
}
