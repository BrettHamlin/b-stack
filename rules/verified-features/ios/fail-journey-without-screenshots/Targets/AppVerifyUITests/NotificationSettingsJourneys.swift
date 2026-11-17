import SettingsInterface
import XCTest

/// Journeys for the feature map entry feature-map/notification-settings.toml. Each test drives AppVerify the way a
/// user would, through JourneyKit, and attaches a screenshot at every checkpoint; scripts/verify.py turns them into
/// evidence.
final class NotificationSettingsJourneys: XCTestCase {
    override func setUp() {
        continueAfterFailure = false
    }

    func testTurningOffSurvivesRelaunch() {
        var screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        XCTAssertEqual(screen.switchValue(NotificationSettingsUIID.toggle), "1", "standard fixture starts with notifications on")

        tapWhenHittable(screen.toggle(NotificationSettingsUIID.toggle))
        waitUntilGone(screen.find(NotificationSettingsUIID.saving))
        XCTAssertEqual(screen.switchValue(NotificationSettingsUIID.toggle), "0", "toggle shows off after the save")

        screen.terminate()
        screen = launchApp(fixture: "standard", reset: false, readyWhen: NotificationSettingsUIID.toggle)
        XCTAssertEqual(screen.switchValue(NotificationSettingsUIID.toggle), "0", "notifications stay off after relaunch")
    }

    func testFailedSaveRevertsAndShowsError() {
        let screen = launchApp(fixture: "save-fails", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        XCTAssertEqual(screen.switchValue(NotificationSettingsUIID.toggle), "1", "save-fails fixture starts with notifications on")

        tapWhenHittable(screen.toggle(NotificationSettingsUIID.toggle))
        let error = screen.find(NotificationSettingsUIID.error)
        XCTAssertTrue(error.waitForExistence(timeout: 10), "an error appears when the save fails")
        XCTAssertEqual(error.label, "Server unavailable")
        XCTAssertEqual(screen.switchValue(NotificationSettingsUIID.toggle), "1", "the toggle reverts to on")
    }
}
