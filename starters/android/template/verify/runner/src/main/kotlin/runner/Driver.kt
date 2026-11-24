package runner

import android.os.Bundle
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.UiObject2
import androidx.test.uiautomator.Until
import core.UiId
import journeykit.Element
import journeykit.Journey
import journeykit.Screen
import java.io.File

private const val WAIT_MS = 10_000L

/** The only code that touches UiAutomator: journey bodies see the app through [Journey], [Screen] and [Element].
 * scripts/verify.py passes the app under test (`bstack.app`) and where screenshots go (`bstack.evidence`). */
class Driver(private val journey: String) : Journey {
    private val arguments: Bundle = InstrumentationRegistry.getArguments()
    private val app: String = arguments.getString("bstack.app") ?: throw IllegalStateException("no bstack.app argument")
    private val device: UiDevice = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
    private val activity: String by lazy {
        device.executeShellCommand("cmd package resolve-activity --brief -c android.intent.category.LAUNCHER $app")
            .trim().lines().last()
    }

    override fun launch(fixture: String): Screen {
        start(fixture, reset = true)
        return AppScreen(fixture)
    }

    private fun start(fixture: String, reset: Boolean) {
        // Every launch starts upright, whatever an earlier journey (or checkout) left on the shared emulator.
        device.setOrientationNatural()
        device.unfreezeRotation()
        device.executeShellCommand("am force-stop $app")
        val output = device.executeShellCommand(
            "am start -W -n $activity --es bstack.fixture $fixture --ez bstack.reset $reset",
        )
        if ("Status: ok" !in output) throw AssertionError("[verify] couldn't start $activity:\n$output")
        device.wait(Until.hasObject(By.pkg(app).depth(0)), WAIT_MS)
    }

    private inner class AppScreen(private val fixture: String) : Screen {
        override fun find(id: UiId): Element {
            node(id)
            return AppElement(id)
        }

        override fun relaunch(): Screen {
            start(fixture, reset = false)
            return this
        }

        override fun rotate() {
            try {
                device.setOrientationLeft()
                device.waitForIdle()
            } finally {
                device.setOrientationNatural()
                device.waitForIdle()
                device.unfreezeRotation()
            }
        }

        override fun returnAfterProcessDeath() {
            device.pressHome()
            device.wait(Until.gone(By.pkg(app).depth(0)), WAIT_MS)
            // `am kill` ends only a process in the background, as the system does when it needs memory; the task and
            // its saved state stay (force-stop would discard them).
            val deadline = System.currentTimeMillis() + WAIT_MS
            while (device.executeShellCommand("pidof $app").isNotBlank()) {
                if (System.currentTimeMillis() > deadline) throw AssertionError("[verify] $app is still running")
                device.executeShellCommand("am kill $app")
                Thread.sleep(200)
            }
            // The same intent as the task's first activity, so the system brings the task back, restoring it.
            val output = device.executeShellCommand("am start -W -n $activity")
            if ("Status: ok" !in output) throw AssertionError("[verify] couldn't return to $activity:\n$output")
            device.wait(Until.hasObject(By.pkg(app).depth(0)), WAIT_MS)
        }

        override fun checkpoint(name: String) {
            val folder = File(arguments.getString("bstack.evidence") ?: "/sdcard/Android/media/bstack", journey)
            folder.mkdirs()
            device.waitForIdle()
            if (!device.takeScreenshot(File(folder, "$name.png"))) throw AssertionError("[verify] screenshot $name failed")
        }
    }

    private inner class AppElement(private val id: UiId) : Element {
        override fun tap() {
            node(id).click()
            device.waitForIdle()
        }

        override fun type(text: String) {
            val node = node(id)
            val field = if (node.className == "android.widget.EditText") node else node.findObject(By.clazz("android.widget.EditText"))
            (field ?: throw AssertionError("[verify] ${id.value} has no text field")).text = text
            device.waitForIdle()
        }

        override fun shows(expected: String) {
            var seen = ""
            val deadline = System.currentTimeMillis() + WAIT_MS
            while (System.currentTimeMillis() < deadline) {
                seen = device.findObject(By.res(id.value))?.let { texts(it).joinToString("\n") } ?: "(not on screen)"
                if (seen == expected) return
                Thread.sleep(100)
            }
            throw AssertionError("[verify] ${id.value} shows:\n$seen\nexpected:\n$expected")
        }

        override fun isDisabled() {
            if (!node(id).wait(Until.enabled(false), WAIT_MS)) throw AssertionError("[verify] ${id.value} is still enabled")
        }
    }

    private fun node(id: UiId): UiObject2 = device.wait(Until.findObject(By.res(id.value)), WAIT_MS)
        ?: throw AssertionError("[verify] no element ${id.value} on screen after ${WAIT_MS / 1000} s")

    /** The node's text, then its children's, in order. An editable field counts as its value only. */
    private fun texts(node: UiObject2): List<String> {
        val own = node.text?.takeIf { it.isNotEmpty() }
        if (node.className == "android.widget.EditText") return listOfNotNull(own)
        val children: List<UiObject2>? = node.children
        return listOfNotNull(own) + children.orEmpty().flatMap { texts(it) }
    }
}
