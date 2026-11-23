package journeys

import journeykit.Journey

fun Journey.probeGo() {
    launch().find("probe.go").tap()
}
