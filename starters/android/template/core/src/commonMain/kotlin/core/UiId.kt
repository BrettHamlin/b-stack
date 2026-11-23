package core

/** Only a feature's api module declares UI identifiers: the build grants this opt-in to api modules alone. */
@RequiresOptIn(
    level = RequiresOptIn.Level.ERROR,
    message = "[typed-ui-identifiers] Only a feature's api module declares UI identifiers. Use one from its <Feature>Ui object.",
)
@Retention(AnnotationRetention.BINARY)
@Target(AnnotationTarget.CONSTRUCTOR)
annotation class DeclaresUiId

/** A UI element's identifier, shared by the view that tags the element and the journeys that find it. Items in a
 * list or grid share one identifier and add their position: `TallyUi.item.at(2)`, `BoardUi.cell.at(row, column)`. */
class UiId private constructor(parts: List<String>) {
    val value: String = parts.joinToString(".")

    @DeclaresUiId
    constructor(value: String) : this(listOf(value))

    /** This identifier for the item at [index] (only integers, so an id can't be built from text). */
    fun at(vararg index: Int): UiId = UiId(listOf(value) + index.map { it.toString() })

    override fun equals(other: Any?): Boolean = other is UiId && other.value == value
    override fun hashCode(): Int = value.hashCode()
    override fun toString(): String = "UiId($value)"
}
