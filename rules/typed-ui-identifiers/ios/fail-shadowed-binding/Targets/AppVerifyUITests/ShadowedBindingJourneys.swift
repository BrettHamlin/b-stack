import XCTest

final class ShadowedBindingJourneys: XCTestCase {
    private func notes() -> String? {
        let controls: [String: String] = ["k": "v"]
        return controls["k"]
    }

    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        let controls = app.switches
        controls["notificationSettings.toggle"].switches.firstMatch.tap()
    }
}
