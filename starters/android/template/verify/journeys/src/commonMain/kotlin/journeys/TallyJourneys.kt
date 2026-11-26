package journeys

import journeykit.Journey
import tally.api.TallyUi

fun Journey.tallyIsSavedAcrossRuns() {
    val screen = launch()
    screen.find(TallyUi.items).shows("(empty)")
    screen.find(TallyUi.name).type("apple")
    screen.find(TallyUi.add).tap()
    screen.find(TallyUi.items).shows("apple 1")
    screen.find(TallyUi.name).type("apple")
    screen.find(TallyUi.add).tap()
    screen.find(TallyUi.items).shows("apple 2")
    screen.checkpoint("counted")
    val again = screen.relaunch()
    again.find(TallyUi.items).shows("apple 2")
    again.checkpoint("after-relaunch")
}

fun Journey.failedSaveKeepsTheOldTally() {
    val screen = launch("FailingSaves")
    screen.find(TallyUi.items).shows("apple 2")
    screen.find(TallyUi.name).type("apple")
    screen.find(TallyUi.add).tap()
    screen.find(TallyUi.error).shows("Couldn't save. The tally is unchanged.")
    screen.find(TallyUi.items).shows("apple 2")
    screen.checkpoint("save-failed")
    screen.relaunch().find(TallyUi.items).shows("apple 2")
}

fun Journey.badNameIsRefused() {
    val screen = launch()
    screen.find(TallyUi.name).type("two words")
    screen.find(TallyUi.add).tap()
    val error = screen.find(TallyUi.error)
    error.shows("Names are 1 to 32 letters, digits, - or _.")
    screen.find(TallyUi.items).shows("(empty)")
    screen.checkpoint("refused")
    screen.find(TallyUi.name).type("fig")
    screen.find(TallyUi.add).tap()
    error.isGone()
    screen.find(TallyUi.items).shows("fig 1")
}

fun Journey.savedTallyIsShownAtStart() {
    val screen = launch("Saved")
    screen.find(TallyUi.items).shows("apple 2\npear 1")
    screen.find(TallyUi.item.at(1)).shows("pear 1")
    screen.checkpoint("saved-at-start")
}

fun Journey.tallySurvivesRotation() {
    val screen = launch()
    screen.find(TallyUi.name).type("fig")
    screen.find(TallyUi.add).tap()
    screen.find(TallyUi.items).shows("fig 1")
    screen.find(TallyUi.name).type("pear")
    screen.rotate()
    screen.find(TallyUi.items).shows("fig 1")
    screen.find(TallyUi.name).shows("pear")
    screen.checkpoint("after-rotation")
}

fun Journey.tallySurvivesProcessDeath() {
    val screen = launch()
    screen.find(TallyUi.name).type("fig")
    screen.find(TallyUi.add).tap()
    screen.find(TallyUi.items).shows("fig 1")
    screen.find(TallyUi.name).type("pear")
    screen.returnAfterProcessDeath()
    screen.find(TallyUi.items).shows("fig 1")
    screen.find(TallyUi.name).shows("pear")
    screen.checkpoint("after-process-death")
}

fun Journey.unreadableTallyIsNeverOverwritten() {
    val screen = launch("Unreadable")
    screen.find(TallyUi.error).shows("The saved tally couldn't be read.")
    screen.find(TallyUi.add).isDisabled()
    screen.checkpoint("load-failed")
    screen.relaunch().find(TallyUi.error).shows("The saved tally couldn't be read.")
}
