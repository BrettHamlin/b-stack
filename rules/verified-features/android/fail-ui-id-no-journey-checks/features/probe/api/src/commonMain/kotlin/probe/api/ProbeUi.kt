package probe.api

import core.UiId

object ProbeUi {
    val go = UiId("probe.go")

    /** Tagged by the view, but no journey checks it. */
    val stop = UiId("probe.stop")
}
