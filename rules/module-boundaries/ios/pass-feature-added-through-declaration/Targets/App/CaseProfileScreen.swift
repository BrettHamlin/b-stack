import Platform
import CaseProfile
import SwiftUI

/// The shipped app composes the new feature with its real storage, from Platform.
struct CaseProfileScreen: View {
    var body: some View { ProfileView(names: StoredName()) }
}
