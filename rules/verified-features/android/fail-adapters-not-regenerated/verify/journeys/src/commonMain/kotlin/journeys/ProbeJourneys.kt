package journeys

import journeykit.Journey
import probe.api.ProbeUi

fun Journey.probeShowsGo() {
    val screen = launch()
    screen.find(ProbeUi.go).tap()
    screen.checkpoint("go")
}
