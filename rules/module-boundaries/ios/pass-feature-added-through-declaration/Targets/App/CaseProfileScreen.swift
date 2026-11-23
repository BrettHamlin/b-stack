import Platform
import CaseProfile
import CaseProfileLogic
import SwiftUI

/// The shipped app composes the new feature with its real storage, from Platform.
struct CaseProfileScreen: View {
    private let store = ProfileScreen.store(names: StoredName())

    var body: some View { ProfileView(store: store) }
}
