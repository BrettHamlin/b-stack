package tally.api

import core.UiId

/** The tally screen's elements, tagged by the view (Modifier.uiId) and found by journeys. */
object TallyUi {
    val name = UiId("tally.name")
    val add = UiId("tally.add")
    val error = UiId("tally.error")
    val items = UiId("tally.items")

    /** One row of the list: `item.at(row)`. */
    val item = UiId("tally.item")
}
