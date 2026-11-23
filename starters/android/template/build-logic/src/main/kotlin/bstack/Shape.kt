package bstack

import groovy.json.JsonSlurper
import java.io.File

/** arch/shape.json: each role's folders, kind and allowed links. The same file scripts/arch.py reads. */
class Role(
    val name: String,
    val folders: List<String>,
    val kind: String,
    val mayUse: List<String>,
    val external: List<String>,
    val compose: Boolean,
    val declaresUiIds: Boolean,
    val optIn: List<String>,
    val testMode: Boolean,
    val fixed: Boolean,
)

class Shape(val roles: List<Role>, val commonTestExternal: List<String>, val testOptIn: List<String>) {
    fun role(name: String): Role = roles.first { it.name == name }

    /** Every module folder (relative to the root, with '/'), with its role. A `*` in a folder matches one folder. */
    fun modules(root: File): List<Pair<String, Role>> = roles.flatMap { role ->
        role.folders.flatMap { pattern -> expand(root, pattern.split('/')) }.map { it to role }
    }.sortedBy { it.first }

    fun roleOf(root: File, relative: String): Role? = modules(root).firstOrNull { it.first == relative }?.second

    private fun expand(root: File, parts: List<String>, prefix: String = ""): List<String> {
        if (parts.isEmpty()) return listOf(prefix)
        val head = parts.first()
        val names = if (head == "*") {
            File(root, prefix).listFiles { f -> f.isDirectory && !f.name.startsWith(".") }?.map { it.name }?.sorted().orEmpty()
        } else listOf(head).filter { File(root, if (prefix.isEmpty()) it else "$prefix/$it").isDirectory }
        return names.flatMap { expand(root, parts.drop(1), if (prefix.isEmpty()) it else "$prefix/$it") }
    }

    companion object {
        fun load(root: File): Shape {
            val json = JsonSlurper().parse(File(root, "arch/shape.json")) as Map<*, *>
            val roles = (json["roles"] as Map<*, *>).map { (name, value) ->
                val r = value as Map<*, *>
                Role(
                    name = name as String,
                    folders = strings(r["folders"]),
                    kind = r["kind"] as String,
                    mayUse = strings(r["may_use"]),
                    external = strings(r["external"]),
                    compose = r["compose"] == true,
                    declaresUiIds = r["declares_ui_ids"] == true,
                    optIn = strings(r["opt_in"]),
                    testMode = r["test_mode"] == true,
                    fixed = r["fixed"] == true,
                )
            }
            return Shape(roles, strings(json["common_test_external"]), strings(json["test_opt_in"]))
        }

        private fun strings(value: Any?): List<String> = (value as List<*>?).orEmpty().map { it as String }
    }
}

/** A module's module.toml: `uses` (module folders), nothing else. `external` is read only to refuse it. */
class ModuleFile(val uses: List<String>, val external: List<String>) {
    companion object {
        private val entry = Regex("""^\s*(uses|external)\s*=\s*\[([^\]]*)]\s*$""", RegexOption.MULTILINE)
        private val item = Regex(""""([^"\\]*)"""")

        fun read(file: File): ModuleFile {
            if (!file.isFile) return ModuleFile(emptyList(), emptyList())
            val text = file.readText().lines().filterNot { it.trim().startsWith("#") }.joinToString("\n")
            val found = entry.findAll(text).toList()
            val rest = entry.replace(text, "").trim()
            if (rest.isNotEmpty()) {
                throw IllegalArgumentException(
                    "[module-boundaries] ${file.path}: a module.toml sets only `uses = [\"<module folder>\", ...]`, on one " +
                        "line. Found: ${rest.lines().first()}",
                )
            }
            fun values(key: String) = found.filter { it.groupValues[1] == key }
                .flatMap { m -> item.findAll(m.groupValues[2]).map { it.groupValues[1] }.toList() }
            return ModuleFile(values("uses"), values("external"))
        }
    }
}

/** gradle/libs.versions.toml's libraries, as "group:name:version" by alias. Read here rather than through Gradle's
 * catalog extension, which projects without a build script don't get before the plugin is applied. The file is
 * code-owned and keeps to `alias = { module = "g:n", version = "v" }` or `version.ref = "key"`. */
class Catalog(private val libraries: Map<String, String>) {
    fun library(alias: String): String = libraries[alias]
        ?: throw IllegalArgumentException("[allowed-dependencies] gradle/libs.versions.toml has no library `$alias`.")

    companion object {
        private val version = Regex("""^([\w-]+)\s*=\s*"([^"]+)"\s*$""")
        private val library = Regex(
            """^([\w-]+)\s*=\s*\{\s*module\s*=\s*"([^"]+)"\s*,\s*version(\.ref)?\s*=\s*"([^"]+)"\s*}\s*$""",
        )

        fun load(root: File): Catalog {
            var section = ""
            val versions = mutableMapOf<String, String>()
            val found = mutableMapOf<String, String>()
            File(root, "gradle/libs.versions.toml").readLines().map { it.trim() }
                .filter { it.isNotEmpty() && !it.startsWith("#") }
                .forEach { line ->
                    if (line.startsWith("[")) {
                        section = line
                    } else if (section == "[versions]") {
                        version.matchEntire(line)?.let { versions[it.groupValues[1]] = it.groupValues[2] }
                    } else if (section == "[libraries]") {
                        val m = library.matchEntire(line)
                            ?: throw IllegalArgumentException("gradle/libs.versions.toml: can't read `$line`")
                        val v = if (m.groupValues[3].isEmpty()) m.groupValues[4] else versions.getValue(m.groupValues[4])
                        found[m.groupValues[1].replace('_', '-')] = "${m.groupValues[2]}:$v"
                    }
                }
            return Catalog(found)
        }
    }
}
