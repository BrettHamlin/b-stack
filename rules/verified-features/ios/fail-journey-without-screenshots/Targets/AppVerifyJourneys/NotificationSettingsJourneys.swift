import SettingsInterface
public import JourneyKit

/// Journeys for the feature map entry feature-map/notification-settings.toml. Each test drives AppVerify the way a
/// user would, through JourneyKit, and attaches a screenshot at every checkpoint; scripts/verify.py turns them into
/// evidence.
public final class NotificationSettingsJourneys: Journey {
    public func testTurningOffSurvivesRelaunch() {
        var screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        expectEqual(screen.switchValue(NotificationSettingsUIID.toggle), "1", "standard fixture starts with notifications on")

        tapWhenHittable(screen.toggle(NotificationSettingsUIID.toggle))
        waitUntilGone(screen.find(NotificationSettingsUIID.saving))
        expectTrue(waitForSwitchValue(screen, NotificationSettingsUIID.toggle, "0"), "toggle shows off after the save")

        screen.terminate()
        screen = launchApp(fixture: "standard", reset: false, readyWhen: NotificationSettingsUIID.toggle)
        expectEqual(screen.switchValue(NotificationSettingsUIID.toggle), "0", "notifications stay off after relaunch")
    }

    public func testFailedSaveRevertsAndShowsError() {
        let screen = launchApp(fixture: "save-fails", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        expectEqual(screen.switchValue(NotificationSettingsUIID.toggle), "1", "save-fails fixture starts with notifications on")

        tapWhenHittable(screen.toggle(NotificationSettingsUIID.toggle))
        let error = screen.find(NotificationSettingsUIID.error)
        expectTrue(error.waitForExistence(timeout: 10), "an error appears when the save fails")
        expectEqual(error.label, "Server unavailable")
        expectEqual(screen.switchValue(NotificationSettingsUIID.toggle), "1", "the toggle reverts to on")
    }
}
