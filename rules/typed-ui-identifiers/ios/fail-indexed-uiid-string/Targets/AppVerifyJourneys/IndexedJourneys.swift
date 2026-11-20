import SettingsInterface
public import JourneyKit

public final class IndexedJourneys: Journey {
    public func testFindsAnIndexedCell() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        expectFalse(screen.find(NotificationSettingsUIID.toggle, at: "3").exists)
    }
}
