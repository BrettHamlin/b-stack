import Harmonize
import Testing

@Test func explicitDependencies() {
    Harmonize.productionCode().variables(includeNested: true)
        .filter { $0.name == "shared" && $0.modifiers.contains(.static) }
        .assertEmpty(rule: Rule(
            id: "explicit-dependencies",
            description: "[explicit-dependencies] No static shared singletons",
            fixHint: "Accept the dependency as an initializer parameter; it's wired up in App."
        ))
}
