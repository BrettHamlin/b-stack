package probe.api

enum class Terrain { Open, Asteroids }

fun Terrain.cost(): Int = when (this) {
    Terrain.Open -> 1
    Terrain.Asteroids -> 2
}
