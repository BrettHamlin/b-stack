# 02 · Layer 1: Can't be written

**Status:** Draft. Discussed and agreed.

The strongest enforcement makes the wrong thing **impossible to express**. The compiler rejects it on every build, the error appears exactly where the mistake is, and there's nothing to argue with.

## Architecture first, enforced right away

Rules and architecture aren't a chicken-and-egg problem. **Architecture is a decision; a rule is that decision made executable.**

1. **Decide the few boundaries that are expensive to change:**
   - process or thread boundaries (UI vs background, client vs server)
   - who owns data and persistence
   - how lifecycle, cancellation and side effects work
   - where platform code lives versus domain logic
2. **Encode them on day one.** Use module structure, types and compiler settings first, and checks where the compiler can't reach.
3. **Build the approved path** for the hard parts, so the easy way and the right way are the same way.
4. **Let everything else grow** from corrections. See [correction-loop](../playbook/correction-loop.md).

Bring in lessons from previous projects as starting rules. Lauren's Dune framework encoded what went wrong in an earlier codebase.

## Mechanisms that work in most languages

| Mechanism | What it enforces | Examples |
|---|---|---|
| **Module/package boundaries** | Which code may depend on which | Rust crates, Go `internal/`, Java/Kotlin modules, Swift packages, TS project references |
| **Visibility** | What a module exposes | `pub`/private, `internal`, `package` |
| **Sum types + exhaustive matching** | Every state handled; new states break callers | Rust/Swift enums, Kotlin sealed classes, TS discriminated unions. Never add a catch-all `default`. |
| **Distinct types for primitives** | No mixing IDs, units or unvalidated input | `struct UserId(u64)`, branded types in TS |
| **Validated types** | Holding the type proves it's valid | Private constructor plus `Email.parse() -> Result<Email>` |
| **Typestate** | Operations exist only in valid states | `Draft<Validated>.send()` exists; `Draft<Unvalidated>.send()` doesn't |
| **Use-once types** | Things happen exactly once | Rust move semantics, Swift `~Copyable` |
| **Concurrency checking** | No data races; clear ownership | Rust `Send`/`Sync`, Swift actors and `Sendable` |
| **Unavailable/deprecated markers with messages** | Retired APIs can't be used; the error names the replacement | `@available(*, unavailable, message:)`, `#[deprecated]` plus deny |
| **Typed errors** | Callers handle a known, closed set of failures | Rust `Result<T, E>`, Swift typed throws |
| **Generated contracts** | API or schema changes break the build | OpenAPI, protobuf or GraphQL code generation; generated asset symbols |
| **Dependencies passed in, not global** | Hidden coupling becomes visible | Constructor injection, no singletons |
| **Warnings as errors** | Soft signals become hard | `-Werror`, `deny(warnings)`, `strict: true` |

## Design the error message

When you retire an API or make something unavailable, write the compiler message for an agent that has no other context:

> `'legacyTimer()' is unavailable: Use TaskScope.run, which cancels when the feature ends`

Name **what to use instead** and **why**. A message that only says "no" pushes the agent toward a workaround.

## Limits of layer 1

- **Escape hatches.** Every language has some: force unwraps, `unsafe`, `@unchecked`, `any`, `# type: ignore`, reflection. The compiler accepts them. Banning them is [layer 2](03-cant-be-merged.md).
- **Configuration.** Compiler strictness lives in editable config. Protecting that config is the [foundation](04-foundation.md).
- **Partial enforcement.** Check each claim against the real toolchain. In Swift, a module can import things it only reaches indirectly, and system frameworks are always importable. So "Domain can't import UI" needs a layer-2 import check.
- **Behaviour.** Types prove structure, not that the feature works. That's [layer 3](05-verification.md).
