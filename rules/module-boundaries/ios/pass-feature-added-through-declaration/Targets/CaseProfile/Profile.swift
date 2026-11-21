import Core
public import CaseProfileInterface
public import CaseProfileLogic
public import ComposableArchitecture
public import SwiftUI

public struct ProfileView: View {
    let store: StoreOf<ProfileScreen>

    public init(names: any NameStoring) {
        store = Store(initialState: ProfileScreen.State()) { ProfileScreen(names: names) }
    }

    public var body: some View {
        Text(store.name)
            .accessibilityIdentifier(ProfileUIID.name.rawValue)
            .onAppear { store.send(.appeared) }
    }
}
