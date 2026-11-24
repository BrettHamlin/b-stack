package core

/** Short text a model keeps for the screen, which survives the system ending the app's process while it's in the
 * background (Android's saved instance state). It holds the screen's session that isn't stored anywhere else: a
 * selection, a half-typed name, a turn the user is in the middle of. What the app keeps goes through a store (a client
 * interface in the feature's api, implemented in a platform module) and isn't copied here: after the process ends, the
 * model loads it from the store again. rememberModel (core-ui) passes each model its own. */
interface Saved {
    operator fun get(key: String): String?

    operator fun set(key: String, value: String)
}

/** A [Saved] that lives as long as the object: for tests, and for a model with nothing to keep. */
class SavedInMemory(vararg values: Pair<String, String>) : Saved {
    private val values = mutableMapOf(*values)

    override fun get(key: String): String? = values[key]

    override fun set(key: String, value: String) {
        values[key] = value
    }
}
