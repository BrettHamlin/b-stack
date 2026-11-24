package journeys

import greeting.api.GreetingUi
import journeykit.Journey

fun Journey.greetingWorks() {
    val screen = launch()
    screen.find(GreetingUi.title).shows("Greeting")
    screen.checkpoint("opened")
    screen.rotate()
    screen.find(GreetingUi.title).shows("Greeting")
    screen.returnAfterProcessDeath()
    screen.find(GreetingUi.title).shows("Greeting")
}
