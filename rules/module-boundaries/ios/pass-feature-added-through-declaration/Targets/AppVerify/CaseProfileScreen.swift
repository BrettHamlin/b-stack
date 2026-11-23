import Fixtures
import CaseProfile
import CaseProfileLogic
import SwiftUI

/// The test-mode app composes it the same way, with a fixture's storage.
struct CaseProfileScreen: View {
    private let store = ProfileScreen.store(names: FixtureName())

    var body: some View { ProfileView(store: store) }
}
