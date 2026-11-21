import XCTest

final class ExtraJourneys: XCTestCase {
    func testOpensTheApp() {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10))
    }
}
