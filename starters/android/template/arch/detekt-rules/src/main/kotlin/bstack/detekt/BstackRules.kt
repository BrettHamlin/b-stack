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
import org.jetbrains.kotlin.analysis.api.symbols.KaCallableSymbol
import org.jetbrains.kotlin.analysis.api.symbols.KaEnumEntrySymbol
import org.jetbrains.kotlin.analysis.api.types.KaFlexibleType
import org.jetbrains.kotlin.idea.references.mainReference
import org.jetbrains.kotlin.lexer.KtTokens
import org.jetbrains.kotlin.psi.KtBinaryExpression
import org.jetbrains.kotlin.psi.KtBinaryExpressionWithTypeRHS
import org.jetbrains.kotlin.psi.KtCatchClause
import org.jetbrains.kotlin.psi.KtDotQualifiedExpression
import org.jetbrains.kotlin.psi.KtExpression
import org.jetbrains.kotlin.psi.KtForExpression
import org.jetbrains.kotlin.psi.KtIfExpression
import org.jetbrains.kotlin.psi.KtImportDirective
import org.jetbrains.kotlin.psi.KtNameReferenceExpression
import org.jetbrains.kotlin.psi.KtReferenceExpression
import org.jetbrains.kotlin.psi.KtThrowExpression
import org.jetbrains.kotlin.psi.psiUtil.getParentOfType
import java.net.URI

/** b-stack's own detekt rules, for what detekt's built-in rules don't cover. Configured in arch/detekt.yml. */
class BstackRules : RuleSetProvider {
    override val ruleSetId = RuleSetId("bstack")

    override fun instance(): RuleSet = RuleSet(ruleSetId, listOf(::NoForceCast, ::NoThrow, ::NoPlatformTypeCall, ::NoSemanticsText, ::NoIfElseOnEnum))
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

/** UiAutomator reads an element's text semantics, and can't tell text Compose drew from text code set: `semantics {
 * text = ... }` (or `clearAndSetSemantics`, or `SemanticsProperties.Text`) replaces what a journey's shows() reads with a
 * string of the code's own, so a wrong number or emoji on screen still passes. Resolved by symbol, so a variable of
 * the app's own named `text` is fine. */
class NoSemanticsText(config: Config) : Rule(
    config,
    "No setting the text semantics: journeys read it as what the user sees.",
    URI("https://github.com/BrettHamlin/b-stack/blob/main/rules/verified-features/rule.toml"),
), RequiresAnalysisApi {
    override fun visitReferenceExpression(expression: KtReferenceExpression) {
        super.visitReferenceExpression(expression)
        if (expression !is KtNameReferenceExpression || expression.getReferencedName() !in NAMES) return
        if (expression.getParentOfType<KtImportDirective>(strict = true) != null) return
        val name = analyze(expression) {
            (expression.mainReference.resolveToSymbol() as? KaCallableSymbol)?.callableId?.asSingleFqName()?.asString()
        }
        if (name !in BANNED) return
        report(
            Finding(
                Entity.from(expression),
                "[verified-features] `${expression.getReferencedName()}` sets the text semantics, which is what journeys " +
                    "read as the text on screen (UiAutomator can't tell it from drawn text), so a journey passes even " +
                    "when what's drawn is wrong. Draw the text with Text(...) and let journeys read that (merge a group " +
                    "with Modifier.semantics(mergeDescendants = true) { }); describe drawing for screen readers with " +
                    "contentDescription. A mark a journey must check that isn't drawn as text (a highlight, an icon) gets a " +
                    "contentDescription saying what it means, which the journey checks with describes().",
            ),
        )
    }

    private companion object {
        val NAMES = setOf("text", "editableText", "Text", "EditableText")
        val BANNED = setOf(
            "androidx.compose.ui.semantics.text",
            "androidx.compose.ui.semantics.editableText",
            "androidx.compose.ui.semantics.SemanticsProperties.Text",
            "androidx.compose.ui.semantics.SemanticsProperties.EditableText",
        )
    }
}

/** `if (side == Side.Blue) ... else ...` treats every other case as the same one, as `else` in a `when` does, so a case
 * added later takes the else branch unseen. In tests (a property test's model of the spec, above all) that hides the
 * new case from the test that should pin it down. Resolved by symbol: only an enum entry counts. */
class NoIfElseOnEnum(config: Config) : Rule(
    config,
    "No if/else on an enum value: a when naming every case.",
    URI("https://github.com/BrettHamlin/b-stack/blob/main/rules/exhaustive-states/rule.toml"),
), RequiresAnalysisApi {
    override fun visitIfExpression(expression: KtIfExpression) {
        super.visitIfExpression(expression)
        if (expression.`else` == null) return
        val condition = expression.condition as? KtBinaryExpression ?: return
        if (condition.operationToken != KtTokens.EQEQ && condition.operationToken != KtTokens.EXCLEQ) return
        val entry = listOfNotNull(condition.left, condition.right).firstNotNullOfOrNull { enumEntry(it) } ?: return
        report(
            Finding(
                Entity.from(expression),
                "[exhaustive-states] `if (${condition.text}) ... else` puts every case but $entry in the else branch, as " +
                    "`else` in a `when` does, so a case added later is handled there unseen. Use a `when` naming every " +
                    "case (the compiler then makes each new case say what it does).",
            ),
        )
    }

    /** The enum entry [expression] names (`Side.Blue`, or `Blue` imported), as `Side.Blue`, or null. */
    private fun enumEntry(expression: KtExpression): String? {
        val name = (expression as? KtDotQualifiedExpression)?.selectorExpression ?: expression
        if (name !is KtNameReferenceExpression) return null
        return analyze(name) {
            (name.mainReference.resolveToSymbol() as? KaEnumEntrySymbol)?.callableId?.asSingleFqName()?.let {
                "${it.parent().shortName()}.${it.shortName()}"
            }
        }
    }
}
