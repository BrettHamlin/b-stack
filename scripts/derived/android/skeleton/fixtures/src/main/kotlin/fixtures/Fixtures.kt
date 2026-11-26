package fixtures

/** Test-mode setups, by name. Journeys launch app-verify with one; the shipped app can't use this module. */
enum class Fixture {
    /** The app as a new user first opens it. */
    Standard,
}

fun fixtureNamed(name: String?): Fixture? = Fixture.entries.firstOrNull { it.name == (name ?: Fixture.Standard.name) }
