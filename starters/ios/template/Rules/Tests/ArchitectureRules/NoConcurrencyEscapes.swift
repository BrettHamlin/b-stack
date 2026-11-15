import Harmonize
import Testing

@Test func noUncheckedSendable() {
    // inheritanceTypesNames drops "@unchecked" (Harmonize 1.3.0), so read the syntax node.
    Harmonize.productionCode().classes(includeNested: true)
        .filter { ($0.node.inheritanceClause?.description ?? "").contains("@unchecked") }
        .assertEmpty(rule: Rule(
            id: "no-concurrency-escapes",
            description: "[no-concurrency-escapes] No @unchecked Sendable",
            fixHint: "Make the type an actor or confine it to the main actor. If neither fits, stop and report."
        ))
}

@Test func noNonisolatedUnsafe() {
    Harmonize.productionCode().variables(includeNested: true)
        .filter { ($0.node.parent?.parent?.description ?? "").contains("nonisolated(unsafe)") }
        .assertEmpty(rule: Rule(
            id: "no-concurrency-escapes",
            description: "[no-concurrency-escapes] No nonisolated(unsafe)",
            fixHint: "Give the state an owner: an actor or the main actor."
        ))
}
