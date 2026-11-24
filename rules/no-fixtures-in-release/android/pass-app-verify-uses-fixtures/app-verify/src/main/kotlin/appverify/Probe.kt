package appverify

import fixtures.Fixture

fun fixtureNames(): List<String> = Fixture.entries.map { it.name }
