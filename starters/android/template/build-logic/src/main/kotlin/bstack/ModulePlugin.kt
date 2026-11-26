package bstack

import com.android.build.api.dsl.ApplicationExtension
import com.android.build.api.dsl.LibraryExtension
import com.android.build.api.dsl.TestExtension
import dev.detekt.gradle.extensions.DetektExtension
import org.gradle.api.GradleException
import org.gradle.api.JavaVersion
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.api.plugins.JavaPluginExtension
import org.gradle.api.tasks.testing.Test
import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import org.jetbrains.kotlin.gradle.dsl.KotlinMultiplatformExtension
import org.jetbrains.kotlin.gradle.tasks.KotlinCompilationTask
import org.jetbrains.kotlin.gradle.dsl.KotlinJvmCompilerOptions

/** Applied to every project. A module gets its role's settings from arch/shape.json (its folder says which role),
 * and its dependencies from its module.toml, which may only name links and libraries the shape gives that role. */
class ModulePlugin : Plugin<Project> {
    override fun apply(project: Project) {
        val root = project.rootDir
        val relative = project.projectDir.relativeTo(root).invariantSeparatorsPath
        val shape = Shape.load(root)
        val role = shape.roleOf(root, relative) ?: return // a folder that only holds modules, like features/
        project.layout.buildDirectory.set(root.resolve(".build/gradle/$relative"))
        val module = if (role.fixed) ModuleFile(emptyList(), emptyList()) else ModuleFile.read(project.file("module.toml"))
        val links = links(shape, root, relative, role, module)
        val catalog = Catalog.load(root)
        val libraries = libraries(relative, role, module).map { catalog.library(it) }

        when (role.kind) {
            "common" -> common(project, role, links, libraries, shape.commonTestExternal.map { catalog.library(it) })
            "android-library", "android-app" -> android(project, relative, role, links, libraries, catalog)
            "android-test" -> runner(project, catalog)
            "jvm", "jvm-tests" -> jvm(project, role, catalog)
            else -> throw GradleException("arch/shape.json: role ${role.name} has unknown kind ${role.kind}")
        }
        project.tasks.withType(KotlinCompilationTask::class.java).configureEach {
            compilerOptions {
                allWarningsAsErrors.set(true)
                progressiveMode.set(true)
                if (role.declaresUiIds) optIn.add("core.DeclaresUiId")
                // Opt-ins are the owner's: per role in arch/shape.json, never @OptIn in code (the arch gate bans it).
                optIn.addAll(role.optIn)
                if (role.kind != "jvm" && role.kind != "jvm-tests" && this@configureEach.name.contains("Test")) {
                    optIn.addAll(shape.testOptIn)
                }
                if (this is KotlinJvmCompilerOptions) jvmTarget.set(JvmTarget.JVM_17)
            }
        }
        if (role.name != "detekt-rules") detekt(project)
    }

    /** Project paths this module may depend on, or a failure naming the rule. */
    private fun links(shape: Shape, root: java.io.File, relative: String, role: Role, module: ModuleFile): List<String> {
        val where = "$relative/module.toml"
        return module.uses.map { target ->
            val targetRole = shape.roleOf(root, target)
                ?: throw GradleException("[module-boundaries] $where: `$target` isn't a module folder. Name a module " +
                    "by its folder, e.g. \"core\" or \"features/<name>/api\".")
            val allowed = role.mayUse.any { entry ->
                val own = entry.endsWith("(own)")
                entry.removeSuffix("(own)") == targetRole.name && (!own || feature(relative) == feature(target))
            }
            if (!allowed) {
                if (targetRole.name == "fixtures") {
                    throw GradleException("[no-fixtures-in-release] $where: $relative may not use fixtures. Only the " +
                        "test-mode app (app-verify) uses fixtures; compose real services in app. If a fixture seems " +
                        "needed there, stop and report.")
                }
                val can = role.mayUse.joinToString(", ").ifEmpty { "nothing" }
                throw GradleException("[module-boundaries] $where: a ${role.name} module may not use $target " +
                    "(a ${targetRole.name} module). A ${role.name} module may use: $can (arch/shape.json). Move the " +
                    "code to a module that may use it, or pass what you need in through an api module. Never edit " +
                    "arch/shape.json or build-logic/; if a link outside the shape seems necessary, stop and report.")
            }
            ":" + target.replace('/', ':')
        }
    }

    /** A module gets every library its role may use (arch/shape.json), so modules of one role resolve the same
     * versions, the ones gradle/verification-metadata.xml lists. A module.toml can't name libraries. */
    private fun libraries(relative: String, role: Role, module: ModuleFile): List<String> {
        if (module.external.isNotEmpty()) {
            val gets = role.external.joinToString(", ").ifEmpty { "none" }
            throw GradleException("[allowed-dependencies] $relative/module.toml: a module can't add libraries " +
                "(${module.external.joinToString(", ")}). A ${role.name} module gets its role's libraries from " +
                "arch/shape.json: $gets. Write the code without it, or stop and report which library you need and " +
                "why: adding one needs the owner (arch/shape.json, gradle/libs.versions.toml, " +
                "gradle/verification-metadata.xml).")
        }
        return role.external
    }

    private fun feature(folder: String): String? = folder.split('/').let { if (it.first() == "features") it.getOrNull(1) else null }

    private fun common(project: Project, role: Role, links: List<String>, libraries: List<String>, testLibraries: List<String>) {
        project.pluginManager.apply("org.jetbrains.kotlin.multiplatform")
        // Persisted data is JSON through kotlinx.serialization, its types @Serializable where the role allows it.
        if (role.serialization) project.pluginManager.apply("org.jetbrains.kotlin.plugin.serialization")
        project.extensions.configure(KotlinMultiplatformExtension::class.java) {
            jvm()
            // A second target makes commonMain real common code: compileCommonMainKotlinMetadata can't see the JDK,
            // so java.io, Thread and System don't exist here. With jvm() alone they would (Kotlin 2.4.21).
            js()
            sourceSets.getByName("commonMain").dependencies {
                links.forEach { implementation(project.project(it)) }
                libraries.forEach { implementation(it) }
            }
            sourceSets.getByName("commonTest").dependencies {
                implementation(kotlin("test"))
                testLibraries.forEach { implementation(it) }
            }
        }
    }

    private fun android(project: Project, relative: String, role: Role, links: List<String>, libraries: List<String>, catalog: Catalog) {
        val namespace = "dev.bstack.starter." + relative.split('/').joinToString(".") { it.replace("-", "") }
        if (role.kind == "android-app") {
            project.pluginManager.apply("com.android.application")
            val appId = project.findProperty("bstack.applicationId") as String
            project.extensions.configure(ApplicationExtension::class.java) {
                this.namespace = namespace
                compileSdk { version = release(37) { minorApiLevel = 2 } }
                defaultConfig {
                    applicationId = if (role.testMode) verifyId(project) else appId
                    minSdk = 29
                    targetSdk = 37
                    versionCode = (project.findProperty("bstack.versionCode") as String).toInt()
                    versionName = project.findProperty("bstack.versionName") as String
                }
                compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
                lint { lint(this) }
                release(project, this, role.testMode)
            }
        } else {
            project.pluginManager.apply("com.android.library")
            project.extensions.configure(LibraryExtension::class.java) {
                this.namespace = namespace
                compileSdk { version = release(37) { minorApiLevel = 2 } }
                defaultConfig { minSdk = 29 }
                compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
                lint { lint(this) }
            }
        }
        if (role.compose) project.pluginManager.apply("org.jetbrains.kotlin.plugin.compose")
        if (role.serialization) project.pluginManager.apply("org.jetbrains.kotlin.plugin.serialization")
        project.dependencies.apply {
            links.forEach { add("implementation", project.project(it)) }
            libraries.forEach { add("implementation", it) }
            add("testImplementation", kotlinLib("test-junit", project))
            add("testImplementation", catalog.library("junit"))
            add("testImplementation", catalog.library("kotlinx-coroutines-test"))
        }
    }

    /** Both apps' release builds: R8 shrinks and obfuscates code and drops unused resources, the same for each, so
     * the journeys can run against what R8 makes of the code (the release gate). The shipped app is signed with the
     * upload key named by the BSTACK_UPLOAD_* environment variables (scripts/package.py; unsigned without them);
     * app-verify, a test app that is never shipped, with the debug key. */
    private fun release(project: Project, android: ApplicationExtension, testMode: Boolean) {
        val env = { name: String -> project.providers.environmentVariable(name).orNull }
        val keystore = env("BSTACK_UPLOAD_KEYSTORE")
        val upload = if (testMode) android.signingConfigs.getByName("debug")
        else if (keystore == null) null else android.signingConfigs.create("upload") {
            storeFile = project.file(keystore)
            storePassword = env("BSTACK_UPLOAD_KEYSTORE_PASSWORD")
            keyAlias = env("BSTACK_UPLOAD_KEY_ALIAS")
            keyPassword = env("BSTACK_UPLOAD_KEY_PASSWORD")
        }
        android.buildTypes.getByName("release") {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(android.getDefaultProguardFile("proguard-android-optimize.txt"))
            signingConfig = upload
        }
    }

    /** Android Lint, the lint gate: only NewApi (a call to an API newer than minSdk 29, which compiles but crashes on
     * older devices), as an error, with no baseline. */
    private fun lint(lint: com.android.build.api.dsl.Lint) {
        lint.checkOnly.add("NewApi")
        lint.error.add("NewApi")
        lint.abortOnError = true
        lint.warningsAsErrors = true
        lint.checkReleaseBuilds = false
        lint.checkTestSources = false
    }

    /** verify/runner: the journeys' driver and generated adapters, a self-instrumenting test app for app-verify. */
    private fun runner(project: Project, catalog: Catalog) {
        project.pluginManager.apply("com.android.test")
        project.extensions.configure(TestExtension::class.java) {
            // A test app's id is its namespace: per checkout, like app-verify's.
            namespace = verifyId(project) + ".runner"
            compileSdk { version = release(37) { minorApiLevel = 2 } }
            defaultConfig {
                minSdk = 29
                targetSdk = 37
                testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
            }
            targetProjectPath = ":app-verify"
            // Its own process, so journeys can stop and relaunch the app under test.
            experimentalProperties["android.experimental.self-instrumenting"] = true
            compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
        }
        project.dependencies.apply {
            add("implementation", project.project(":verify:journeys"))
            add("implementation", project.project(":verify:journeykit"))
            add("implementation", project.project(":core"))
            listOf("uiautomator", "androidx-test-runner", "androidx-test-junit", "junit").forEach {
                add("implementation", catalog.library(it))
            }
        }
    }

    /** app-verify's application id: one per checkout (from its path), so two checkouts' installs never replace each
     * other's on the shared emulator. The shipped app keeps bstack.applicationId. */
    private fun verifyId(project: Project): String {
        val digest = java.security.MessageDigest.getInstance("SHA-256").digest(project.rootDir.absolutePath.toByteArray())
        val checkout = digest.take(4).joinToString("") { "%02x".format(it) }
        return "${project.findProperty("bstack.applicationId")}.verify.c$checkout"
    }

    private fun jvm(project: Project, role: Role, catalog: Catalog) {
        project.pluginManager.apply("org.jetbrains.kotlin.jvm")
        project.extensions.configure(JavaPluginExtension::class.java) {
            sourceCompatibility = JavaVersion.VERSION_17
            targetCompatibility = JavaVersion.VERSION_17
        }
        fun lib(alias: String) = catalog.library(alias)
        project.dependencies.apply {
            if (role.name == "konsist") {
                add("testImplementation", lib("konsist"))
                add("testImplementation", lib("junit"))
                add("testImplementation", kotlinLib("test-junit", project))
            } else {
                add("compileOnly", lib("detekt-api"))
            }
        }
        if (role.name == "detekt-rules") {
            // The jar is named by its sources' hash: a Gradle daemon keeps the detekt rule classes it loaded from a jar
            // path (detekt 2.0.0-alpha.6), so a changed rule gets a new path and is loaded fresh.
            val sources = project.fileTree("src").files.sortedBy { it.path }
            val digest = java.security.MessageDigest.getInstance("SHA-256")
            sources.forEach { digest.update(it.relativeTo(project.projectDir).invariantSeparatorsPath.toByteArray()); digest.update(it.readBytes()) }
            val hash = digest.digest().take(6).joinToString("") { "%02x".format(it) }
            project.tasks.withType(org.gradle.jvm.tasks.Jar::class.java).configureEach { archiveVersion.set(hash) }
        }
        if (role.name == "konsist") {
            project.tasks.withType(Test::class.java).configureEach {
                // Konsist reads the sources itself, so Gradle can't tell when they changed: always run.
                outputs.upToDateWhen { false }
                systemProperty("bstack.root", project.rootDir.absolutePath)
            }
        }
    }

    private fun detekt(project: Project) {
        project.pluginManager.apply("dev.detekt")
        project.extensions.configure(DetektExtension::class.java) {
            config.setFrom(project.rootProject.file("arch/detekt.yml"))
            buildUponDefaultConfig.set(false)
            parallel.set(true)
        }
        project.dependencies.add("detektPlugins", project.project(":arch:detekt-rules"))
    }

    private fun kotlinLib(module: String, project: Project): String =
        "org.jetbrains.kotlin:kotlin-$module:${org.jetbrains.kotlin.gradle.plugin.getKotlinPluginVersion(project.logger)}"
}
