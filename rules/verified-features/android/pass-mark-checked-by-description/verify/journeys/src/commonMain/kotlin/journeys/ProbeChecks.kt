package journeys

import journeykit.Element

/** For journeys: a cell the selected piece can move to. Its highlight is a drawn stroke, so the check reads the cell's
 * description, not its text. */
fun Element.isReachable() = describes("Open space, can move here")
