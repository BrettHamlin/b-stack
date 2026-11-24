package journeykit

import core.UiId

/** What a journey body gets: it starts the test-mode app and sees it only through [Screen]. The runner
 * (verify/runner, generated adapters plus the UiAutomator driver) implements it; journey bodies can't reach
 * UiAutomator, Android or the JVM at all. */
interface Journey {
    /** Starts app-verify on a fresh copy of [fixture]'s data (a fixtures.Fixture name). */
    fun launch(fixture: String = "Standard"): Screen
}

interface Screen {
    /** The element tagged with [id] (Modifier.uiId in the view). Fails if it doesn't appear. */
    fun find(id: UiId): Element

    /** Stops the app and starts it again on the same data. */
    fun relaunch(): Screen

    /** Turns the device to landscape and back, as a user does; the activity is recreated each time. */
    fun rotate()

    /** Leaves the app for the home screen, has the system end its process there (as it does to free memory), and
     * returns to it: the screen comes back in a new process, from what it saved. */
    fun returnAfterProcessDeath()

    /** Saves a screenshot named [name] as the journey's evidence. Each journey saves at least one. */
    fun checkpoint(name: String)
}

interface Element {
    fun tap()

    /** Replaces the element's text, as typing does. */
    fun type(text: String)

    /** Waits until the element (with everything inside it) shows exactly [expected], one text per line. */
    fun shows(expected: String)

    /** Waits until the element (with everything inside it) is described exactly as [expected], one content description
     * per line: what a screen reader says for it. For a mark that isn't drawn as text (a highlight, an icon, a Canvas
     * stroke), the view gives the element a contentDescription saying what the mark means, and the journey checks it
     * here. */
    fun describes(expected: String)

    /** Waits until the element is selected (a chosen tab, option or piece: Modifier.selectable's or Tab's `selected`). */
    fun isSelected()

    /** Waits until the element is gone from the screen (a dismissed dialog, a removed piece). */
    fun isGone()

    /** Waits until the element can't be used (a disabled button or field). */
    fun isDisabled()
}
