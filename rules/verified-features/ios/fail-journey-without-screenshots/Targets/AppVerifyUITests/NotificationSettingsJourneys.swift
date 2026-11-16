import SettingsInterface
import XCTest

/// Journeys for the feature map entry feature-map/notification-settings.toml. Each test drives AppVerify the way a
/// user would and attaches a screenshot at every checkpoint; scripts/verify.py turns them into evidence.
final class NotificationSettingsJourneys: XCTestCase {
    override func setUp() {
        continueAfterFailure = false
    }

    func testTurningOffSurvivesRelaunch() {
        var app = launch(fixture: "standard", reset: true)
        XCTAssertEqual(toggleValue(app), "1", "standard fixture starts with notifications on")
        capture(app, "1-starts-on")

        tapToggle(app)
        waitForSaveToFinish(app)
        XCTAssertEqual(toggleValue(app), "0", "toggle shows off after the save")
        capture(app, "2-turned-off")

        app.terminate()
        app = launch(fixture: "standard", reset: false)
        XCTAssertEqual(toggleValue(app), "0", "notifications stay off after relaunch")
        capture(app, "3-still-off-after-relaunch")
    }

    func testFailedSaveRevertsAndShowsError() {
        let app = launch(fixture: "save-fails", reset: true)
        XCTAssertEqual(toggleValue(app), "1", "save-fails fixture starts with notifications on")
        capture(app, "1-starts-on")

        tapToggle(app)
        // A Text row in a Form is exposed as a cell, so match the identifier on any element type.
        let error = app.descendants(matching: .any)[NotificationSettingsUIID.error]
        XCTAssertTrue(error.waitForExistence(timeout: 10), "an error appears when the save fails")
        XCTAssertEqual(error.label, "Server unavailable")
        XCTAssertEqual(toggleValue(app), "1", "the toggle reverts to on")
        capture(app, "2-reverted-with-error")
    }

    private func launch(fixture: String, reset: Bool) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["BSTACK_FIXTURE"] = fixture
        if reset {
            app.launchEnvironment["BSTACK_RESET"] = "1"
        }
        app.launch()
        XCTAssertTrue(app.switches[NotificationSettingsUIID.toggle].waitForExistence(timeout: 20), "settings screen is ready")
        return app
    }

    private func toggleValue(_ app: XCUIApplication) -> String? {
        app.switches[NotificationSettingsUIID.toggle].value as? String
    }

    private func tapToggle(_ app: XCUIApplication) {
        // A SwiftUI Toggle in a Form is a cell containing the switch; tapping the cell's centre lands on the label.
        let control = app.switches[NotificationSettingsUIID.toggle].switches.firstMatch
        let hittable = expectation(for: NSPredicate(format: "isHittable == true"), evaluatedWith: control)
        wait(for: [hittable], timeout: 10)
        control.tap()
    }

    private func waitForSaveToFinish(_ app: XCUIApplication) {
        let saving = app.descendants(matching: .any)[NotificationSettingsUIID.saving]
        let gone = expectation(for: NSPredicate(format: "exists == false"), evaluatedWith: saving)
        wait(for: [gone], timeout: 10)
    }

    private func capture(_ app: XCUIApplication, _ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        _ = attachment
    }
}
