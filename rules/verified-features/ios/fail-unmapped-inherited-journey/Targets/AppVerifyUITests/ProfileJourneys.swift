import SettingsInterface
import XCTest

/// The test is declared only on the base class, so ProfileJourneys runs it as ProfileJourneys/testEditsName.
class JourneyBase: XCTestCase {
    func testEditsName() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        XCTAssertTrue(screen.find(NotificationSettingsUIID.toggle).exists)
    }
}

final class ProfileJourneys: JourneyBase, @unchecked Sendable {}
