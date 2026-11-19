public import Core
internal import XCTest

// The XCUITest boundary. Keep XCTest internal and this framework resilient: journey bodies compile without
// testing search paths. Never expose an XCUI type (including from an element or a screenshot) in this API.

/// The running AppVerify, as journeys see it.
@MainActor
public struct Screen {
    private let app: XCUIApplication

    fileprivate init(app: XCUIApplication) { self.app = app }

    /// The element with this identifier, whatever its type.
    public func find(_ id: UIID) -> Element {
        Element(app.descendants(matching: .any)[id.rawValue])
    }

    /// The control to tap for a SwiftUI Toggle with this identifier. A Toggle in a Form is a switch wrapping a
    /// switch; tapping the outer one's centre lands on the label and does nothing.
    public func toggle(_ id: UIID) -> Element {
        Element(app.switches[id.rawValue].switches.firstMatch)
    }

    /// A Toggle's value: "1" on, "0" off.
    public func switchValue(_ id: UIID) -> String? {
        switchElement(id).value as? String
    }

    fileprivate func switchElement(_ id: UIID) -> XCUIElement {
        app.switches[id.rawValue]
    }

    public func terminate() {
        app.terminate()
    }

    fileprivate func screenshot() -> XCUIScreenshot {
        app.screenshot()
    }

    /// A button in a system alert, such as a permission prompt. System UI can't carry our identifiers.
    public func systemAlertButton(_ label: String) -> Element {
        Element(XCUIApplication(bundleIdentifier: "com.apple.springboard").buttons[label])
    }

    /// A key on the software keyboard.
    public func keyboardKey(_ label: String) -> Element {
        Element(app.keyboards.buttons[label])
    }
}

/// A typed element handle. Its raw element and constructor are private to JourneyKit.
@MainActor
public struct Element {
    fileprivate let raw: XCUIElement

    fileprivate init(_ raw: XCUIElement) { self.raw = raw }

    public var exists: Bool { raw.exists }
    public var label: String { raw.label }
    public func tap() { raw.tap() }
    public func typeText(_ text: String) { raw.typeText(text) }
    public func waitForExistence(timeout: Double) -> Bool { raw.waitForExistence(timeout: timeout) }
}

/// Base for journey bodies. The XCTestCase adapter supplies itself; bodies never receive the test or the raw app.
@MainActor
open class Journey {
    private let test: XCTestCase

    public init(test: AnyObject) {
        guard let test = test as? XCTestCase else { preconditionFailure("Journey requires an XCTestCase adapter") }
        self.test = test
    }

    public func expectTrue(_ value: @autoclosure () -> Bool, _ message: String = "",
                           file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertTrue(value(), message, file: file, line: line)
    }

    public func expectFalse(_ value: @autoclosure () -> Bool, _ message: String = "",
                            file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertFalse(value(), message, file: file, line: line)
    }

    public func expectEqual<T: Equatable>(_ actual: @autoclosure () -> T, _ expected: @autoclosure () -> T,
                                          _ message: String = "", file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertEqual(actual(), expected(), message, file: file, line: line)
    }

    /// Launches AppVerify with a fixture and records which one, so verify.py can check it against the feature map,
    /// then waits until `ready` exists. `reset` restores the fixture's starting data; launch without it to check
    /// what survived a relaunch.
    public func launchApp(fixture: String, reset: Bool, readyWhen ready: UIID) -> Screen {
        let record = XCTAttachment(string: fixture)
        record.name = "fixture-\(fixture)"
        record.lifetime = .keepAlways
        test.add(record)
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
    public func tapWhenHittable(_ element: Element, timeout: Double = 10) {
        let hittable = test.expectation(for: NSPredicate(format: "isHittable == true"), evaluatedWith: element.raw)
        test.wait(for: [hittable], timeout: timeout)
        element.tap()
    }

    /// Waits until a Toggle shows `expected` ("1" on, "0" off). UI updates land a moment after a tap, especially on a
    /// loaded machine; asserting immediately is flaky. Returns false if it never does, so a swallowed tap still fails.
    public func waitForSwitchValue(_ screen: Screen, _ id: UIID, _ expected: String, timeout: Double = 10) -> Bool {
        let settled = XCTNSPredicateExpectation(predicate: NSPredicate(format: "value == %@", expected),
                                                object: screen.switchElement(id))
        return XCTWaiter().wait(for: [settled], timeout: timeout) == .completed
    }

    public func waitUntilGone(_ element: Element, timeout: Double = 10) {
        let gone = test.expectation(for: NSPredicate(format: "exists == false"), evaluatedWith: element.raw)
        test.wait(for: [gone], timeout: timeout)
    }

    /// Attaches a screenshot to the result; verify.py turns these into evidence.md.
    public func capture(_ screen: Screen, _ name: String) {
        let attachment = XCTAttachment(screenshot: screen.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        test.add(attachment)
    }
}
