package probe.logic

import kotlin.random.Random

fun average(scores: List<Int>): Double? = if (scores.isEmpty()) null else scores.sum().toDouble() / scores.size

fun shuffled(scores: List<Int>, seed: Int): List<Int> = scores.shuffled(Random(seed))
