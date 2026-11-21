import MeterInterface
import JourneyKit

// Only the extension itself is banned here: the body uses no reserved name, so this case isolates that check.
extension XCTest.XCUIElement {
    func nothing() {}
}

final class ExtensionLookupJourneys: Journey {
    func testAddsOne() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: MeterUIID.increment)
        screen.find(MeterUIID.increment).nothing()
    }
}
