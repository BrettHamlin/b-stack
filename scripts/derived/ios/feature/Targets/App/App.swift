import Greeting
import GreetingLogic
import SwiftUI

@main
struct StarterApp: App {
    private let greeter = Greeter.store()

    var body: some Scene {
        WindowGroup {
            GreeterView(store: greeter)
        }
    }
}
