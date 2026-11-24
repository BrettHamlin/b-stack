package bstack.detekt

import dev.detekt.api.Config
import dev.detekt.api.Entity
import dev.detekt.api.Finding
import dev.detekt.api.Rule
import dev.detekt.api.RuleSet
import dev.detekt.api.RuleSetId
import dev.detekt.api.RuleSetProvider
import org.jetbrains.kotlin.lexer.KtTokens
import org.jetbrains.kotlin.psi.KtBinaryExpressionWithTypeRHS
import org.jetbrains.kotlin.psi.KtCatchClause
import org.jetbrains.kotlin.psi.KtThrowExpression
import java.net.URI

/** b-stack's own detekt rules, for what detekt's built-in rules don't cover. Configured in arch/detekt.yml. */
class BstackRules : RuleSetProvider {
    override val ruleSetId = RuleSetId("bstack")

    override fun instance(): RuleSet = RuleSet(ruleSetId, listOf(::NoForceCast, ::NoThrow))
}

/** `x as T` throws when x isn't a T: a force cast. `as?` with a fallback is the safe form. */
class NoForceCast(config: Config) : Rule(
    config,
    "No force casts: `as` throws when the value isn't that type.",
    URI("https://github.com/BrettHamlin/b-stack/blob/main/rules/no-force-operations/rule.toml"),
) {
    override fun visitBinaryWithTypeRHSExpression(expression: KtBinaryExpressionWithTypeRHS) {
        super.visitBinaryWithTypeRHSExpression(expression)
        if (expression.operationReference.getReferencedNameElementType() == KtTokens.AS_KEYWORD) {
            report(
                Finding(
                    Entity.from(expression),
                    "[no-force-operations] `as` is a force cast. Use `as?` and handle null, or a `when (x) { is T -> }`; " +
                        "if the value truly can't be another type, model that in the type instead.",
                ),
            )
        }
    }
}

/** `throw` crashes the caller unless someone catches it: the same as `!!` or error(). Results are sealed types. */
class NoThrow(config: Config) : Rule(
    config,
    "No throw: return a sealed result the caller must handle.",
    URI("https://github.com/BrettHamlin/b-stack/blob/main/rules/no-force-operations/rule.toml"),
) {
    override fun visitThrowExpression(expression: KtThrowExpression) {
        super.visitThrowExpression(expression)
        if (rethrowsItsCatch(expression)) return
        report(
            Finding(
                Entity.from(expression),
                "[no-force-operations] `throw` crashes the caller unless someone catches it. Return a sealed result " +
                    "the caller must handle (like Stored.Failed), or make the type rule the case out.",
            ),
        )
    }
}

/** `catch (e: CancellationException) { cleanup(); throw e }`: passing on what was caught, not a new failure. */
private fun rethrowsItsCatch(expression: KtThrowExpression): Boolean {
    val thrown = expression.thrownExpression?.text ?: return false
    var parent = expression.parent
    while (parent != null) {
        if (parent is KtCatchClause) return parent.catchParameter?.name == thrown
        parent = parent.parent
    }
    return false
}
