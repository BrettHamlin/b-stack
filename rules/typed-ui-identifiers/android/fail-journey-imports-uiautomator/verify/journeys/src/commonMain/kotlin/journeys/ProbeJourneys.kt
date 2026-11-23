package journeys

import androidx.test.uiautomator.UiDevice
import journeykit.Journey

fun Journey.probeGo() {
    UiDevice.getInstance(null).pressBack()
}
