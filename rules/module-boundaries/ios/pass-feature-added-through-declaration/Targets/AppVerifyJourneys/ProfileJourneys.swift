import ProfileInterface
public import JourneyKit

public final class ProfileJourneys: Journey {
    public func testShowsTheName() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: ProfileUIID.name)
        expectEqual(screen.find(ProfileUIID.name).label, "Ada")
        capture(screen, "1-shows-name")
    }
}
