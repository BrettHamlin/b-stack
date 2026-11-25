package journeys

import journeykit.Journey
import probe.api.ProbeUi

fun Journey.probeShowsGo() {
    val screen = launch()
    screen.rotate()
    screen.returnAfterProcessDeath()
    screen.find(ProbeUi.go).shows("Go")
    screen.checkpoint("go")
}
