# Evidence: <change title>

Draft format; to be refined in the verification discussion.

| | |
|---|---|
| Commit / build | `<sha>` / `<build number or checksum>` |
| Platform | <OS version, simulator or device, model> |
| Fixture / config | <fixture account, feature flags, backend> |
| Claim | <what this change makes true> |
| Feature map | `<feature id>` @ `<revision>` |

## Checks run
- Build: pass/fail
- Rules: pass/fail
- Tests: <which>, pass/fail

## Journey
| Step | Expected | Observed | Evidence |
|---|---|---|---|
| 1. <action> | <result> | <result> | <screenshot/log link> |

## Durable effects
<What was checked outside the UI: saved data, backend state, after a relaunch.>

## Not covered
<Surfaces, platforms or failure cases this evidence doesn't prove.>
