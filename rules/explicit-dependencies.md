# explicit-dependencies

**Status:** Draft
**Layer:** 1

## Problem
Singletons and globals (`Store.shared`) hide coupling from the compiler, can't be swapped for tests or fixtures, and let any code reach any service. Agents use them because they're the shortest path.

## Layer
Layer 1. When dependencies only arrive through initializers, the compiler forces every caller to provide them, and fixtures and fakes can be swapped in for [verification](../guide/05-verification.md).

## Enforcement
- Dependencies are initializer parameters, typically protocols defined in the consuming module
- One composition root (app startup) builds the real graph; test and fixture modes build alternatives
- Layer 2: ban `static let shared` / global mutable state outside the composition root

## Error message
> Global service access isn't allowed. Accept this dependency as an initializer parameter; it's wired up in the composition root. If threading it through feels wrong, stop and report; the module boundaries may need adjusting.

## Escape hatches
- Static or global state → layer-2 ban
- Service-locator lookups → layer-2 ban on the locator outside the composition root

## Origin
Our discussion. Also required by verification: launching in a known state needs swappable dependencies.
