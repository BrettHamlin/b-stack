import Core
import CaseProfileInterface
public import CaseProfileLogic
public import ComposableArchitecture
public import SwiftUI

public struct ProfileView: View {
    let store: StoreOf<ProfileScreen>

    public init(store: StoreOf<ProfileScreen>) {
        self.store = store
    }

    public var body: some View {
        Text(store.name)
            .accessibilityIdentifier(ProfileUIID.name.rawValue)
            .onAppear { store.send(.appeared) }
    }
}
