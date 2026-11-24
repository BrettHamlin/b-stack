import Core
import GreetingInterface
public import GreetingLogic
public import ComposableArchitecture
public import SwiftUI

public struct GreeterView: View {
    @Bindable var store: StoreOf<Greeter>

    public init(store: StoreOf<Greeter>) {
        self.store = store
    }

    public var body: some View {
        VStack {
            TextField("Name", text: $store.name.sending(\.nameChanged))
                .accessibilityIdentifier(GreeterUIID.name.rawValue)
            Button("Greet") { store.send(.greet(PersonName(store.name))) }
                .accessibilityIdentifier(GreeterUIID.greet.rawValue)
            Text(store.shown)
                .accessibilityIdentifier(GreeterUIID.shown.rawValue)
        }
    }
}
