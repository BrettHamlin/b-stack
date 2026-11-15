# Platforms

The [guide](../guide/) is language-neutral. Each file here says how its layers and the [rules](../rules/) look on one stack.

| Platform | Status |
|---|---|
| [iOS / Swift](ios-swift.md) | Draft; layer 1 verified |

## Adding a platform

Create `<platform>.md` with these sections: recommended shape, layer 1 settings, what the compiler actually enforces (**tested**, not assumed), layer 2 checks, foundation, layer 3 verification, and a **rule mapping** table with a row for every rule in the catalog. `scripts/check_guide.py` fails if a rule is missing from any platform file.

Test compiler claims against the real toolchain before writing them down. The Swift tests found that module boundaries were weaker than expected.
