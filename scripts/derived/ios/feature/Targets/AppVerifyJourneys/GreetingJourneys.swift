import GreetingInterface
public import JourneyKit

/// Journeys for feature-map/greeting.toml.
public final class GreetingJourneys: Journey {
    public func testGreetsTheNameTypedIn() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: GreeterUIID.name)
        tapWhenHittable(screen.find(GreeterUIID.name))
        screen.find(GreeterUIID.name).typeText("Ada")
        tapWhenHittable(screen.find(GreeterUIID.greet))
        let shown = screen.find(GreeterUIID.shown)
        expectTrue(shown.waitForExistence(timeout: 10), "the greeting appears")
        expectEqual(shown.label, "Hello, Ada!")
        capture(screen, "1-greeted")
    }
}
