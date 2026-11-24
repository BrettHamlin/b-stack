package journeys

import journeykit.Journey
import probe.api.ProbeUi

fun Journey.probeShowsGo() {
    val screen = launch()
    screen.checkpoint("opened")
    screen.rotate()
    screen.returnAfterProcessDeath()
    screen.find(ProbeUi.go).shows(
        "Write this journey: use the probe feature as a user would, check what they'd see, and that it survives the " +
            "device turning and the process ending.",
    )
}
