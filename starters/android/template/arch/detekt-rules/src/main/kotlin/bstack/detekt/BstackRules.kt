package bstack.detekt

import dev.detekt.api.Config
import dev.detekt.api.RequiresAnalysisApi
import dev.detekt.api.Entity
import dev.detekt.api.Finding
import dev.detekt.api.Rule
import dev.detekt.api.RuleSet
import dev.detekt.api.RuleSetId
import dev.detekt.api.RuleSetProvider
import org.jetbrains.kotlin.analysis.api.analyze
import org.jetbrains.kotlin.analysis.api.types.KaFlexibleType
import org.jetbrains.kotlin.lexer.KtTokens
import org.jetbrains.kotlin.psi.KtBinaryExpressionWithTypeRHS
import org.jetbrains.kotlin.psi.KtCatchClause
import org.jetbrains.kotlin.psi.KtDotQualifiedExpression
import org.jetbrains.kotlin.psi.KtExpression
import org.jetbrains.kotlin.psi.KtForExpression
import org.jetbrains.kotlin.psi.KtThrowExpression
import java.net.URI

/** b-stack's own detekt rules, for what detekt's built-in rules don't cover. Configured in arch/detekt.yml. */
class BstackRules : RuleSetProvider {
    override val ruleSetId = RuleSetId("bstack")

    override fun instance(): RuleSet = RuleSet(ruleSetId, listOf(::NoForceCast, ::NoThrow, ::NoPlatformTypeCall))
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

/** A Java result without nullability annotations has a platform type (`File!`): Kotlin lets `.` and `for` use it as
 * if it can't be null, and a null crashes there, as `!!` would (`dir.listFiles().forEach { }`). */
class NoPlatformTypeCall(config: Config) : Rule(
    config,
    "No member calls or loops on Java results of unknown nullability: give them a Kotlin type first.",
    URI("https://github.com/BrettHamlin/b-stack/blob/main/rules/no-force-operations/rule.toml"),
), RequiresAnalysisApi {
    override fun visitDotQualifiedExpression(expression: KtDotQualifiedExpression) {
        super.visitDotQualifiedExpression(expression)
        if (isPlatformType(expression.receiverExpression)) {
            report(expression.receiverExpression, "`${expression.receiverExpression.text}.`")
        }
    }

    override fun visitForExpression(expression: KtForExpression) {
        super.visitForExpression(expression)
        val range = expression.loopRange ?: return
        if (isPlatformType(range)) report(range, "`for (... in ${range.text})`")
    }

    /** A flexible type that may be null but is used as non-null (`File!`). After `?.` its lower bound is nullable,
     * which the compiler already makes code handle; a type flexible only in mutability or variance
     * (`(Mutable)List<T>` from a non-null Java collection) has a non-null upper bound and is fine. */
    private fun isPlatformType(expression: KtExpression): Boolean = analyze(expression) {
        val type = expression.expressionType
        type is KaFlexibleType && !type.lowerBound.isMarkedNullable && type.upperBound.isMarkedNullable
    }

    private fun report(expression: KtExpression, use: String) {
        report(
            Finding(
                Entity.from(expression),
                "[no-force-operations] $use uses a Java result whose nullability Kotlin doesn't know (a platform type), " +
                    "as if it can't be null; if it is, this crashes, as `!!` would. Give it a type first: " +
                    "`val files: Array<File>? = dir.listFiles()`, then handle null (`?.`, `?:`, `orEmpty()`).",
            ),
        )
    }
}
