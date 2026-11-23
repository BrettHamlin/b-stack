package journeys

import journeykit.Journey

fun Journey.probeGo() {
    Class.forName("androidx.test.uiautomator.UiDevice")
}
