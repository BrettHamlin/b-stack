import Core
import XCTest

// JourneyKit: the only file in the journeys that touches XCUITest's lookup API. typed-ui-identifiers rejects that API
// (queries such as .switches or .descendants, matching(...), XCUIApplication, NSPredicate, .identifier) in every other
// journey file. Journeys find elements by UIID, which only *Interface modules can create, so a renamed or invented
// identifier fails to compile. Code-owned (CODEOWNERS): add a helper here rather than reaching for the raw API.

/// The running AppVerify, as journeys see it.
struct Screen {
    fileprivate let app: XCUIApplication

    /// The element with this identifier, whatever its type.
    func find(_ id: UIID) -> XCUIElement {
        app.descendants(matching: .any)[id.rawValue]
    }

    /// The control to tap for a SwiftUI Toggle with this identifier. A Toggle in a Form is a switch wrapping a
    /// switch; tapping the outer one's centre lands on the label and does nothing.
    func toggle(_ id: UIID) -> XCUIElement {
        app.switches[id.rawValue].switches.firstMatch
    }

    /// A Toggle's value: "1" on, "0" off.
    func switchValue(_ id: UIID) -> String? {
        app.switches[id.rawValue].value as? String
    }

    func terminate() {
        app.terminate()
    }

    func screenshot() -> XCUIScreenshot {
        app.screenshot()
    }

    /// A button in a system alert, such as a permission prompt. System UI can't carry our identifiers.
    func systemAlertButton(_ label: String) -> XCUIElement {
        XCUIApplication(bundleIdentifier: "com.apple.springboard").buttons[label]
    }

    /// A key on the software keyboard.
    func keyboardKey(_ label: String) -> XCUIElement {
        app.keyboards.buttons[label]
    }
}

extension XCTestCase {
    /// Launches AppVerify with a fixture and records which one, so verify.py can check it against the feature map,
    /// then waits until `ready` exists. `reset` restores the fixture's starting data; launch without it to check
    /// what survived a relaunch.
    func launchApp(fixture: String, reset: Bool, readyWhen ready: UIID) -> Screen {
        let record = XCTAttachment(string: fixture)
        record.name = "fixture-\(fixture)"
        record.lifetime = .keepAlways
        add(record)
        let app = XCUIApplication()
        app.launchEnvironment["BSTACK_FIXTURE"] = fixture
        if reset {
            app.launchEnvironment["BSTACK_RESET"] = "1"
        }
        app.launch()
        let screen = Screen(app: app)
        XCTAssertTrue(screen.find(ready).waitForExistence(timeout: 20), "\(ready) is on screen after launch")
        return screen
    }

    /// Waits until the element can be tapped (right after launch it may exist but not be hittable yet), then taps it.
    func tapWhenHittable(_ element: XCUIElement, timeout: TimeInterval = 10) {
        let hittable = expectation(for: NSPredicate(format: "isHittable == true"), evaluatedWith: element)
        wait(for: [hittable], timeout: timeout)
        element.tap()
    }

    func waitUntilGone(_ element: XCUIElement, timeout: TimeInterval = 10) {
        let gone = expectation(for: NSPredicate(format: "exists == false"), evaluatedWith: element)
        wait(for: [gone], timeout: timeout)
    }

    /// Attaches a screenshot to the result; verify.py turns these into evidence.md.
    func capture(_ screen: Screen, _ name: String) {
        let attachment = XCTAttachment(screenshot: screen.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
