import Foundation
import MeterInterface
public import JourneyKit

public final class TypedLookupJourneys: Journey {
    private let env: [String: String] = ["CI": "1"]

    public func testAddsOne() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: MeterUIID.increment)
        // Never app.switches["meter.increment"]: find it by the constant.
        tapWhenHittable(screen.toggle(MeterUIID.increment))
        expectTrue(screen.find(MeterUIID.increment).exists)

        var built = [String: String]()
        built["a"] = "1"
        let notes: [String: String] = ["result": "toggled"]
        let lookup = { (values: [String: String]) in values["CI"] }
        expectEqual(notes["result"], "toggled")
        expectEqual(self.env["CI"], lookup(env))
        expectEqual(built["a"], "1")
        _ = ProcessInfo.processInfo.environment["CI"]
        _ = Locale(identifier: "en_US_POSIX")
        _ = Locale.current.identifier
        _ = TimeZone(identifier: "UTC")
        _ = notes.keys
        let site = "https://example.com"
        expectFalse(site.isEmpty)

        if screen.systemAlertButton("Allow").exists {
            screen.systemAlertButton("Allow").tap()
        }
        if screen.keyboardKey("Return").exists {
            screen.keyboardKey("Return").tap()
        }
    }
}
