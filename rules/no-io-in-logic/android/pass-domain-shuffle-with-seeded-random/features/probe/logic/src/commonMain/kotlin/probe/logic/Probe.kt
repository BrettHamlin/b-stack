package probe.logic

import kotlin.random.Random

class Deck(private val random: Random, private val cards: List<Int>) {
    fun shuffle(): Deck = Deck(random, cards.shuffled(random))
}

fun dealt(deck: Deck): Deck = deck.shuffle()
