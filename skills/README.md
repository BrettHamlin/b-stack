# Skills

Procedures for agents, as plain `SKILL.md` folders (usable from Claude Code, Codex and others).

| Skill | Use when |
|---|---|
| [new-project](new-project/SKILL.md) | Asked to start, create or scaffold a new app |
| [correction-loop](correction-loop/SKILL.md) | The user corrects you, or the same review comment comes up twice |
| [art-eval](art-eval/SKILL.md) | A project needs graphics (sprites, icons, 3D models, animation, characters, backgrounds), or you're choosing a model or method to make them |

## Principles for judgment calls

Apply these when no rule or skill covers the situation:

1. **Push every constraint as high as it goes:** impossible to write (types, modules, API) → blocked by a check → caught by verification → prose, last.
2. **Never weaken enforcement.** No suppression comments, config edits, new dependencies or CI changes to get past a check.
3. **If the right fix isn't possible within the rules, stop and report** what blocks you and what you'd change. That's a successful outcome.
4. **A ban needs a replacement.** Don't forbid something without a supported way to do it right.
5. **Verify claims against the real toolchain**, and say what you didn't verify.
