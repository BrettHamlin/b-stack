import XCTest

/// The test is declared only on the base class, so ProfileJourneys runs it as ProfileJourneys/testEditsName.
class JourneyBase: XCTestCase {
    func testEditsName() {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10))
    }
}

final class ProfileJourneys: JourneyBase, @unchecked Sendable {}
