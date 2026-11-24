package core

/** Short text a model keeps for the screen, which survives the system ending the app's process while it's in the
 * background (Android's saved instance state). For what the user was in the middle of, like a half-typed name; data
 * goes to a store. rememberModel (core-ui) passes each model its own. */
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
