package journeys

import journeykit.Journey

internal fun Journey.probeHidden() {
    launch().checkpoint("hidden")
}
