package bstack.konsist

import com.lemonappdev.konsist.api.Konsist
import com.lemonappdev.konsist.api.declaration.KoFileDeclaration
import java.io.File
import kotlin.test.Test
import kotlin.test.fail

/**
 * The architecture rules Kotlin's compiler and detekt don't cover, as Konsist tests (the Kotlin tool Harmonize, the
 * iOS starter's checker, is modeled on). Konsist parses the sources; most checks read declarations, the rest the text
 * of function bodies, so they are heuristics without type information. Each failure line starts with the b-stack rule
 * it enforces and says what to do instead.
 */
class ArchitectureTest {
    private val root = File(System.getProperty("bstack.root") ?: error("bstack.root isn't set"))

    /** Every Kotlin file in the project's modules (not build-logic or arch/, which are code-owned). */
    private val files: List<Source> by lazy {
        val skip = listOf(".build/", ".tools/", "build/", "build-logic/", "arch/", ".gradle/", ".kotlin/")
        Konsist.scopeFromExternalDirectory(root.absolutePath).files
            .map { Source(it, it.path.removePrefix(root.absolutePath).removePrefix("/")) }
            .filter { source -> skip.none { source.relative.startsWith(it) } }
    }

    private class Source(val file: KoFileDeclaration, val relative: String) {
        val text: String get() = file.text
        val test: Boolean get() = "/src/commonTest/" in relative || "/src/test/" in relative
        val module: String get() = relative.substringBefore("/src/")
        val role: String
            get() = when {
                module == "core" -> "core"
                module == "core-ui" -> "core-ui"
                module.startsWith("features/") -> module.substringAfterLast('/')
                module.startsWith("platform/") -> "platform"
                module == "verify/runner" -> "runner"
                module.startsWith("verify/") -> module.substringAfter('/')
                else -> module
            }
        val compositionRoot: Boolean get() = role == "app" || role == "app-verify"
    }

    private fun check(findings: List<String>) {
        if (findings.isNotEmpty()) fail(findings.joinToString("\n"))
    }

    /** `text` with comments and string contents blanked out, so names in them don't count. Offsets are kept. */
    private fun code(text: String): String {
        val out = StringBuilder(text)
        var i = 0
        while (i < text.length) {
            when {
                text.startsWith("//", i) -> while (i < text.length && text[i] != '\n') out[i++] = ' '
                text.startsWith("/*", i) -> {
                    val end = text.indexOf("*/", i + 2).let { if (it < 0) text.length else it + 2 }
                    while (i < end) { if (text[i] != '\n') out[i] = ' '; i++ }
                }
                text[i] == '"' -> {
                    val triple = text.startsWith("\"\"\"", i)
                    val close = if (triple) "\"\"\"" else "\""
                    i += close.length
                    while (i < text.length && !text.startsWith(close, i)) {
                        if (!triple && text[i] == '\\') { out[i] = ' '; i++ }
                        if (i < text.length && text[i] != '\n') out[i] = ' '
                        i++
                    }
                    i += close.length
                }
                else -> i++
            }
        }
        return out.toString()
    }

    private fun line(text: String, offset: Int) = text.substring(0, offset).count { it == '\n' } + 1

    /** Each match of [pattern] in the code of [sources], as "<rule> path:line: <message>". */
    private fun matches(sources: List<Source>, pattern: Regex, message: (MatchResult) -> String): List<String> =
        sources.flatMap { source ->
            val code = code(source.text)
            pattern.findAll(code).map { "${source.relative}:${line(code, it.range.first)}: ${message(it)}" }.toList()
        }

    @Test
    fun moduleBoundaries() = check(
        matches(
            files.filter { it.role == "ui" && !it.test },
            Regex("""^\s*import\s+((?:java|javax|android)\.[\w.]+)""", RegexOption.MULTILINE),
        ) {
            "[module-boundaries] a feature's ui module renders state and sends actions with Compose; it doesn't use " +
                "the platform directly (`${it.groupValues[1]}`). Put platform work in a platform module behind the " +
                "feature api's client interface, and pass it in from the app."
        },
    )

    @Test
    fun uiReachesNoContext() = check(
        matches(files.filter { it.role == "ui" && !it.test }, Regex("""\bLocalContext\b""")) {
            "[module-boundaries] a feature's ui module doesn't reach the platform through LocalContext. Put platform " +
                "work in a platform module behind the feature api's client interface, and pass it in from the app."
        },
    )

    @Test
    fun ioOnlyInPlatform() = check(
        matches(
            files.filter { !it.test && it.role in setOf("app", "app-verify", "ui", "core-ui", "core", "api", "logic") },
            Regex("""^\s*import\s+((?:java\.io|java\.net|java\.nio|android\.database|android\.content\.SharedPreferences|androidx\.datastore|androidx\.room|okhttp3|io\.ktor)\b[\w.*]*)|\b(getSharedPreferences|openFileInput|openFileOutput|openOrCreateDatabase|deleteFile|getExternalFilesDir)\s*\(""", RegexOption.MULTILINE),
        ) {
            "[io-only-in-platform] `${(it.groupValues[1].ifEmpty { it.groupValues[2] }).trim()}` does I/O outside a " +
                "platform module. Define a client interface in the feature's api module, implement it in a platform " +
                "module (and a fake in fixtures), and pass it in from the app."
        },
    )

    @Test
    fun thinApp() {
        val app = files.filter { it.role == "app" && !it.test }
        val found = matches(
            app,
            Regex("""\b(if|when|for|while|do|try|launch|async|runCatching)\b\s*[({]|\b(LaunchedEffect|SideEffect|DisposableEffect)\b|^\s*(?:private\s+|internal\s+)?fun\s""", RegexOption.MULTILINE),
        ) {
            "[thin-app] `${it.value.trim()}`: the shipped app only composes (an Application that builds services, " +
                "Activities that show each feature's screen with a model). Decisions and side effects go in a " +
                "feature's logic, where tests and journeys run them."
        }.toMutableList()
        app.forEach { source ->
            source.file.functions(includeNested = true).filterNot { it.hasOverrideModifier }.forEach {
                found += "${source.relative}: [thin-app] fun ${it.name}: the shipped app declares no functions of its " +
                    "own (overriding onCreate is how it composes)."
            }
            source.file.classes(includeNested = true)
                .filterNot { cls -> cls.parents().any { it.name in setOf("Application", "ComponentActivity") } }
                .forEach {
                    found += "${source.relative}: [thin-app] class ${it.name}: the shipped app holds only its " +
                        "Application and Activities; types go in a feature or platform module."
                }
        }
        check(found.distinct())
    }

    @Test
    fun viewsHoldNoClients() {
        // Interfaces declared in api and logic modules are the clients platform implements; a view never sees one.
        val clients = files.filter { !it.test && it.role in setOf("api", "logic") }
            .flatMap { source -> source.file.interfaces(includeNested = true).filterNot { it.hasSealedModifier }.map { it.name } }
            .toSet()
        check(
            files.filter { !it.test && it.role == "ui" }.flatMap { source ->
                val code = code(source.text)
                clients.filter { Regex("""\b${Regex.escape(it)}\b""").containsMatchIn(code) }.map {
                    "${source.relative}: [views-hold-no-clients] the view names $it, a client. A view gets only its " +
                        "model (`TallyRoute(model)`); the app builds the model from the clients with rememberModel, " +
                        "and the model calls them."
                }
            },
        )
    }

    @Test
    fun typedIdentifiers() = check(
        matches(
            files.filter { it.role in setOf("core", "api") && !it.test },
            Regex("""\btypealias\s+(\w+)\s*=\s*(String|Int|Long|Short|Byte|Double|Float|Boolean|Char|UInt|ULong)\b"""),
        ) {
            "[typed-identifiers] `typealias ${it.groupValues[1]} = ${it.groupValues[2]}` is the same type to the " +
                "compiler, so any ${it.groupValues[2]} passes for it. Declare `@JvmInline value class " +
                "${it.groupValues[1]}(val value: ${it.groupValues[2]})`."
        },
    )

    @Test
    fun explicitDependencies() {
        val main = files.filter { !it.test }
        val found = mutableListOf<String>()
        main.forEach { source ->
            val file = source.file
            file.properties(includeNested = false).filter { it.isTopLevel && it.isVar }.forEach {
                found += "${source.relative}: top-level `var ${it.name}`"
            }
            file.objects(includeNested = true).forEach { obj ->
                obj.properties(includeNested = false).filter { it.isVar }.forEach {
                    found += "${source.relative}: `var ${it.name}` in object ${obj.name}"
                }
                val parents = obj.parents().map { it.name.substringBefore('<').trim().substringAfterLast('.') }
                // A sealed type's case: a data object whose parents are sealed types declared in the same module.
                val sealedCase = obj.hasDataModifier && parents.isNotEmpty() && parents.all { parent ->
                    val declared = Regex("""\bsealed\s+(?:interface|class)\s+${Regex.escape(parent)}\b""")
                    main.any { it.module == source.module && declared.containsMatchIn(it.text) }
                }
                val uiIds = obj.name.endsWith("Ui") && source.role == "api" && parents.isEmpty()
                val name = if (obj.hasCompanionModifier) "companion object of ${outerName(obj)}" else "object ${obj.name}"
                if (!sealedCase && !uiIds && parents.isNotEmpty()) {
                    found += "${source.relative}: $name implements ${parents.joinToString()}, so it is a singleton " +
                        "service (a sealed type's case is a `data object`, its sealed type in the same module)"
                }
                obj.properties(includeNested = false)
                    .filterNot { it.hasConstModifier }
                    .filterNot { uiIds && (Regex("""=\s*UiId\s*\(""").containsMatchIn(it.text) || computed(it.text)) }
                    .filterNot { sealedCase && it.hasOverrideModifier && (literal(it.text) || computed(it.text)) }
                    .filterNot { obj.hasCompanionModifier && (it.hasPrivateModifier || ownValue(obj, it.text) || computed(it.text)) }
                    .forEach { found += "${source.relative}: $name holds `val ${it.name}`, a global" }
            }
        }
        val holders = Regex("""\b(mutableListOf|mutableMapOf|mutableSetOf|mutableStateOf|MutableStateFlow|MutableSharedFlow|ArrayList|HashMap|HashSet|AtomicInteger|AtomicLong|AtomicReference)\s*[(<]|\bby\s+lazy\b""")
        main.forEach { source ->
            source.file.properties(includeNested = false).filter { it.isTopLevel }.forEach { property ->
                if (holders.containsMatchIn(code(property.text))) {
                    found += "${source.relative}: top-level `${property.name}` holds mutable state or a lazy service"
                }
            }
            source.file.objects(includeNested = true).forEach { obj ->
                obj.properties(includeNested = false).filter { holders.containsMatchIn(code(it.text)) }.forEach {
                    found += "${source.relative}: `${it.name}` in object ${obj.name} holds mutable state or a lazy service"
                }
            }
        }
        found += matches(main.filter { it.role != "core-ui" }, Regex("""\b(staticCompositionLocalOf|compositionLocalOf)\b""")) {
            "`${it.value}` is a service locator"
        }
        check(found.map {
            "[explicit-dependencies] $it. Pass dependencies in through constructors and function parameters; " +
                "app and app-verify compose them. If shared state seems necessary, stop and report."
        })
    }

    private fun outerName(obj: com.lemonappdev.konsist.api.declaration.KoObjectDeclaration): String =
        (obj.containingDeclaration as? com.lemonappdev.konsist.api.provider.KoNameProvider)?.name ?: ""

    /** A literal (number in any base, with underscores or a suffix; boolean; null; string or raw string without
     * templates; char) or a dotted name, with no call. Blanked text (code()) still has the quotes. */
    private val VALUE = """(?:true|false|null|-?(?:0[xXbB][\w_]+|[\d_.]+(?:[eE][-+]?\d+)?)[LFfuU]*|""\"[^$]*""\"|"[^"$]*"|'(?:\\u[0-9a-fA-F]{4}|\\?.)'|[A-Za-z_][\w.]*)"""

    /** A property computed on each read from a name or literal (`val limit: Int get() = LIMIT`), holding nothing.
     * A getter that calls or constructs something (`get() = Repository(...)`) still counts as holding it. */
    private fun computed(text: String): Boolean = !templated(text) &&
        Regex("""^[^=]*\bget\s*\(\s*\)\s*=\s*$VALUE\s*$""").containsMatchIn(declaration(text).trim())

    /** A property whose value is a literal or a name (`override val retryable = false`, `= Kind.Main`): case data, not
     * a service. A call (`= Http(...)`) is still a service; a named object is scanned in its own right. */
    private fun literal(text: String): Boolean = !templated(text) &&
        Regex("""^(?:override\s+)?val\s+\w+\s*(?::\s*[\w.<>?, *()\->@]+)?\s*=\s*$VALUE\s*$""").matches(declaration(text).trim())

    /** A string template in the property's own text (`"${Http().base}/v1"`): code() blanks string contents, so this
     * reads the original. A template can call anything, so it's never a plain value. */
    private fun templated(text: String): Boolean {
        val code = code(text)
        val start = Regex("""\b(val|var)\b""").find(code)?.range?.first ?: 0 // the property itself, not its KDoc
        var i = start
        while (i < text.length) {
            when {
                text.startsWith("//", i) -> i = text.indexOf('\n', i).let { if (it < 0) text.length else it }
                text.startsWith("/*", i) -> i = text.indexOf("*/", i + 2).let { if (it < 0) text.length else it + 2 }
                text.startsWith("\"\"\"", i) -> { // a raw string: every ${ is a template
                    val end = text.indexOf("\"\"\"", i + 3).let { if (it < 0) text.length else it }
                    if ("\${" in text.substring(i + 3, end)) return true
                    i = end + 3
                }
                text[i] == '"' -> { // a string: ${ is a template unless the $ itself is escaped
                    i++
                    while (i < text.length && text[i] != '"') {
                        if (text[i] == '\\') { i += 2; continue }
                        if (text.startsWith("\${", i)) return true
                        i++
                    }
                    i++
                }
                else -> i++
            }
        }
        return false
    }

    /** A property's text from `val`/`var` on: annotations, KDoc and comments before it dropped. */
    private fun declaration(text: String): String =
        code(text).let { it.substring(Regex("""\b(val|var)\b""").find(it)?.range?.first ?: 0) }

    /** A data or value class's companion value of its own type, such as `val Empty = Tally(emptyMap())`: a
     * constant, not a service (a service class's `val shared = Repository(...)` still fails). */
    private fun ownValue(obj: com.lemonappdev.konsist.api.declaration.KoObjectDeclaration, text: String): Boolean {
        val outer = obj.containingDeclaration as? com.lemonappdev.konsist.api.declaration.KoClassDeclaration ?: return false
        return (outer.hasDataModifier || outer.hasValueModifier) &&
            Regex("""=\s*${Regex.escape(outer.name)}\s*\(""").containsMatchIn(text)
    }

    @Test
    fun stateIsOwned() = check(
        files.filter { it.role == "logic" && !it.test }.flatMap { source ->
            source.file.classes(includeNested = true).filterNot { it.hasPrivateModifier }.flatMap { cls ->
                cls.properties(includeNested = false)
                    .filterNot { it.hasPrivateModifier || Regex("""\bprivate\s+set\b""").containsMatchIn(code(it.text)) }
                    .filter { it.isVar || Regex("""\bMutable\w*\b|\bmutable\w*Of\b""").containsMatchIn(declaration(it.text)) }
                    .map {
                        "${source.relative}: [explicit-dependencies] ${cls.name}.${it.name} is state others can change. A " +
                            "model keeps its state private (`private val current = MutableStateFlow(...)`) and exposes " +
                            "`val state: StateFlow<...>`; the view changes it only through send(action)."
                    }
            }
        },
    )

    @Test
    fun noConcurrencyEscapes() {
        val main = files.filter { !it.test && it.role != "runner" }
        // Only where the file imports the kotlinx.coroutines name, so a domain type called Job is fine. (Threads, locks
        // and thread pools are detekt's: ForbiddenMethodCall resolves them.)
        val scopes = matches(main.filter { !it.compositionRoot }, Regex("""\b(CoroutineScope|MainScope|SupervisorJob|Job)\s*\(""")) {
            "[no-concurrency-escapes] `${it.groupValues[1]}(` makes a scope nobody cancels. Launch in the scope you " +
                "were given (the composition root owns scopes and passes them in)."
        }.filter { finding ->
            val source = main.first { finding.startsWith(it.relative + ":") }
            val name = Regex("""`(\w+)\(`""").find(finding)?.groupValues?.get(1)
            Regex("""^\s*import\s+kotlinx\.coroutines\.(\*|$name)\s*$""", RegexOption.MULTILINE).containsMatchIn(source.text)
        } + matches(main.filter { !it.compositionRoot }, Regex("""\bkotlinx\.coroutines\.(CoroutineScope|MainScope|SupervisorJob|Job)\s*\(""")) {
            "[no-concurrency-escapes] `${it.groupValues[1]}(` makes a scope nobody cancels. Launch in the scope you " +
                "were given (the composition root owns scopes and passes them in)."
        }
        // A Thread subclass: detekt sees `Thread()` calls, not a supertype's constructor. A domain class of its own
        // named Thread (declared or imported in the file) is fine.
        val subclasses = matches(main, Regex(""":\s*(?:java\.lang\.)?Thread\s*\(""")) {
            "[no-concurrency-escapes] a Thread subclass outlives everything and can't be cancelled. Launch in the " +
                "scope you were given."
        }.filter { finding ->
            val source = main.first { finding.startsWith(it.relative + ":") }
            !Regex("""\bclass\s+Thread\b|^\s*import\s+[\w.]+\.Thread\s*$""", RegexOption.MULTILINE).containsMatchIn(source.text) ||
                Regex("""^\s*import\s+java\.lang\.Thread\s*$""", RegexOption.MULTILINE).containsMatchIn(source.text)
        }
        val threads = matches(
            main,
            Regex("""@Volatile\b|@Synchronized\b|^\s*import\s+java\.util\.concurrent\.(?!TimeUnit\b)[\w.*]+|\bDispatchers\.Unconfined\b""", RegexOption.MULTILINE),
        ) {
            "[no-concurrency-escapes] `${it.value.trim()}` works around coroutines' structured concurrency. Use the " +
                "scope and dispatcher you were given, and a Mutex or a single owner for shared state. If neither fits, " +
                "stop and report what you're trying to share."
        }
        check(scopes + subclasses + threads)
    }

    @Test
    fun typedUiIdentifiers() {
        val found = mutableListOf<String>()
        found += matches(files.filter { it.role != "core-ui" && it.role != "runner" }, Regex("""\btestTag\b""")) {
            "[typed-ui-identifiers] tag elements with Modifier.uiId(<Feature>Ui.<element>), never a raw testTag."
        }
        found += matches(files.filter { it.module != "core" }, Regex("""\bDeclaresUiId\b""")) {
            "[typed-ui-identifiers] only core names DeclaresUiId; feature api modules get its opt-in from the build."
        }
        files.filter { it.module != "core" }.forEach { source ->
            val code = code(source.text)
            Regex("""\bUiId\s*\(""").findAll(code).forEach { call ->
                val inUiObject = source.role == "api" &&
                    source.file.objects(includeNested = false).any { obj ->
                        obj.name.endsWith("Ui") && obj.properties(includeNested = false).any { property ->
                            Regex("""^\s*(?:public\s+)?val\s+\w+\s*(?::\s*UiId\s*)?=\s*UiId\s*\(\s*"\s*"\s*\)\s*$""")
                                .matches(declaration(property.text).trim()) &&
                                !Regex("""UiId\s*\(\s*"[^"]*\$""").containsMatchIn(property.text) &&
                                source.text.indexOf(property.text).let { start -> call.range.first in start until start + property.text.length }
                        }
                    }
                if (!inUiObject) {
                    found += "${source.relative}:${line(code, call.range.first)}: [typed-ui-identifiers] a UiId is " +
                        "declared only as `val <element> = UiId(\"<feature>.<element>\")` in a <Feature>Ui object in " +
                        "the feature's api module. Use one from there."
                }
            }
        }
        check(found)
    }

    @Test
    fun noIoInLogic() = check(
        matches(
            files.filter { it.role == "logic" && !it.test },
            Regex("""\b(println|print|readln|readlnOrNull)\s*\(|\bClock\.System\b|\bTimeSource\.Monotonic\b|\bRandom\.(Default|next\w*)\b|\.(random|randomOrNull|shuffled|shuffle)\s*\(\s*\)|\bmeasureTime(?:Millis|Nanos)?\s*[({]"""),
        ) {
            "[no-io-in-logic] `${it.value.trimEnd('(').trim()}` reaches the outside world (console, clock or " +
                "unseeded randomness). Pass in a seeded Random, or define what you need as an interface in the " +
                "feature's api module, implement it in a platform module, and pass it in."
        }.filterNot { finding ->
            // The feature's own method of that name (a Deck's shuffle()), not the standard library's.
            val name = Regex("""`\.(\w+)\(\)`""").find(finding)?.groupValues?.get(1) ?: return@filterNot false
            val module = finding.substringBefore("/src/").substringBeforeLast('/')
            files.any { it.module.startsWith(module) && Regex("""\bfun\s+(?:[\w.<>]+\.)?$name\s*\(""").containsMatchIn(it.text) }
        },
    )

    @Test
    fun exhaustiveTests() {
        val tests = files.filter { it.test }
        val found = mutableListOf<String>()
        found += matches(
            tests,
            Regex("""\b(cancelAndIgnoreRemainingEvents|cancelAndConsumeRemainingEvents|skipItems|expectMostRecentItem|expectMostRecentItemOrNull|testIn|turbineScope|assertTrue|assertFalse|assertNotNull|assertContains|assertNotEquals)\b"""),
        ) {
            "[exhaustive-tests] `${it.value}` lets a change the test didn't expect pass. Assert whole values with " +
                "assertEquals(expected, actual), and consume every state with assertEquals(<state>, awaitItem()) " +
                "inside test { }. If the whole value can't be pinned down, stop and report."
        }
        tests.forEach { source ->
            val code = code(source.text)
            Regex("""(?:\bthis\.)?\bawaitItem\s*\(\s*\)""").findAll(code).forEach { call ->
                val before = code.substring(0, call.range.first).trimEnd().removeSuffix("this.").trimEnd()
                val after = code.substring(call.range.last + 1).trimStart()
                val asActual = before.endsWith(",") || Regex("""\bactual\s*=$""").containsMatchIn(before)
                val wholeArgument = asActual && (after.startsWith(",") || after.startsWith(")"))
                if (enclosingCall(code, call.range.first) != "assertEquals" || !wholeArgument) {
                    found += "${source.relative}:${line(code, call.range.first)}: [exhaustive-tests] every awaitItem() " +
                        "is the whole actual value of an assertEquals (`assertEquals(<whole state>, awaitItem())`), so " +
                        "each state the flow emits is checked whole."
                }
            }
        }
        files.filter { it.role == "logic" && !it.test }.forEach { source ->
            source.file.classes(includeNested = true).forEach { cls ->
                cls.properties(includeNested = false)
                    .filter { !it.hasPrivateModifier && !it.hasInternalModifier && it.name != "state" && exposesStateFlow(it.text) }
                    .forEach {
                        found += "${source.relative}: [exhaustive-tests] ${cls.name}.${it.name}: a model exposes its " +
                            "state as `val state: StateFlow<...>`, the one name tests read it by (state.test { })."
                    }
            }
        }
        found += matches(
            tests.filter { it.role == "logic" },
            Regex("""\bstate\s*\.\s*(let|run|apply|also|takeIf|takeUnless|onEach|replayCache)\b|\bwith\s*\([^()]*\bstate\s*\)"""),
        ) {
            "[exhaustive-tests] read the model's state only through state.test { } (Turbine), not " +
                "`${it.value.trim()}`, so every state it emits is asserted."
        }
        found += matches(
            tests.filter { it.role == "logic" },
            Regex("""\bstate\s*\.\s*(value|first|firstOrNull|single|singleOrNull|last|lastOrNull|collect\w*|take|drop|toList|filter\w*|map\w*)\b"""),
        ) {
            "[exhaustive-tests] read the model's state only through state.test { } (Turbine), not " +
                "state.${it.groupValues[1]}, so every state it emits is asserted."
        }
        check(found)
    }

    /** A property declared `: StateFlow<...>` (or Mutable) or made with asStateFlow()/stateIn(...). */
    private fun exposesStateFlow(text: String): Boolean =
        Regex("""^[^=]*:\s*(?:Mutable)?StateFlow\s*<|\.(asStateFlow|stateIn)\s*\(""").containsMatchIn(code(text))

    /** [text] without a type-argument list at its end (`assertEquals<Map<String, List<Int>>>` -> `assertEquals`). */
    private fun withoutTypeArguments(text: String): String {
        val trimmed = text.trimEnd()
        if (!trimmed.endsWith(">")) return trimmed
        var depth = 0
        for (i in trimmed.indices.reversed()) {
            when (trimmed[i]) {
                '>' -> if (i == 0 || trimmed[i - 1] != '-') depth++ // `->` in a function type isn't a bracket
                '<' -> if (--depth == 0) return trimmed.substring(0, i)
            }
        }
        return trimmed
    }

    /** The name of the call whose parentheses enclose [offset], if any. */
    private fun enclosingCall(code: String, offset: Int): String? {
        var depth = 0
        var braces = 0
        var i = offset - 1
        while (i >= 0) {
            when (code[i]) {
                ')' -> depth++
                '(' -> if (depth == 0 && braces == 0) {
                    return Regex("""(\w+)\s*$""").find(withoutTypeArguments(code.substring(0, i)))?.groupValues?.get(1)
                } else if (depth > 0) depth--
                '}' -> braces++ // a whole lambda before the call, e.g. `expected = buildList { ... }`
                '{' -> if (braces == 0) return null else braces--
            }
            i--
        }
        return null
    }

    @Test
    fun everyTestAsserts() = check(
        files.filter { it.test }.flatMap { source ->
            val asserts = Regex("""\b(assert\w*|fail)\s*[(<]""")
            val helpers = source.file.functions(includeNested = true)
                .filter { fn -> fn.annotations.none { it.name == "Test" } && asserts.containsMatchIn(code(fn.text)) }
                .map { it.name }
            source.file.functions(includeNested = true)
                .filter { fn -> fn.annotations.any { it.name == "Test" } }
                .filterNot { fn ->
                    asserts.containsMatchIn(code(fn.text)) ||
                        helpers.any { Regex("""\b${Regex.escape(it)}\s*\(""").containsMatchIn(code(fn.text)) }
                }
                .map {
                    "${source.relative}: [exhaustive-tests] test `${it.name}` asserts nothing, so it passes whatever the " +
                        "code does. Assert the whole result (assertEquals), or delete the test."
                }
        } + files.map { it.module }.distinct().filter { it.startsWith("features/") && it.endsWith("/logic") }
            .filter { module -> files.none { it.module == module && it.test && "@Test" in it.text } }
            .map {
                "$it: [tests-always-run] a feature's logic has tests (src/commonTest, Turbine for its state). Add them " +
                    "with the feature."
            },
    )

    @Test
    fun testsAlwaysRun() = check(
        matches(files.filter { it.test }, Regex("""@(?:\w+\.)*(Ignore|Disabled)\b|\bassume(True|False|That)\s*\(|\bAssume\.""")) {
            "[tests-always-run] `${it.value}` skips a test. Every test runs: fix the code or the test, or stop and report."
        },
    )
}
