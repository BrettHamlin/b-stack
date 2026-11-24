package bstack

import com.android.build.api.dsl.ApplicationExtension
import com.android.build.api.dsl.LibraryExtension
import com.android.build.api.dsl.Lint
import com.android.build.api.dsl.TestExtension
import dev.detekt.gradle.Detekt
import org.gradle.api.Project
import org.gradle.api.tasks.testing.Test
import org.jetbrains.kotlin.gradle.dsl.KotlinJvmCompilerOptions
import org.jetbrains.kotlin.gradle.tasks.KotlinCompilationTask

/** `bstackSettings` on the root project: writes the enforcement settings in effect, after everything that configures
 * them has run, to .build/settings/effective.json for scripts/settings.py (the settings gate), which compares them
 * with arch/settings.json. It reads what Gradle, Kotlin, the Android plugin and detekt will use, not this plugin's
 * source, so a setting changed anywhere (gradle.properties, settings.gradle.kts, an init script) shows here. */
internal fun registerSettingsDump(root: Project) {
    val out = root.rootDir.resolve(".build/settings/effective.json")
    val effective = root.provider { groovy.json.JsonOutput.prettyPrint(groovy.json.JsonOutput.toJson(effective(root))) }
    root.tasks.register("bstackSettings") {
        notCompatibleWithConfigurationCache("reads every project's settings as they stand when it runs")
        outputs.upToDateWhen { false }
        doLast {
            out.parentFile.mkdirs()
            out.writeText(effective.get())
        }
    }
}

private fun effective(root: Project): Map<String, Any?> {
    val gradle = root.gradle
    val start = gradle.startParameter
    return mapOf(
        "build" to mapOf(
            "dependencyVerification" to start.dependencyVerificationMode.name,
            "buildCache" to start.isBuildCacheEnabled,
            "initScripts" to (start.allInitScripts.map { it.name } +
                (gradle.gradleUserHomeDir.resolve("init.d").listFiles()?.map { "init.d/${it.name}" } ?: emptyList())).sorted(),
            "offline" to start.isOffline,
            // detekt skips every analysis when this property is set (detekt 2.0.0-alpha.6).
            "detektDryRun" to root.providers.gradleProperty("detekt-dry-run").orNull,
        ),
        "modules" to root.subprojects.filter { it.tasks.withType(KotlinCompilationTask::class.java).isNotEmpty() }
            .associate { it.projectDir.relativeTo(root.rootDir).invariantSeparatorsPath to module(it) }
            .toSortedMap(),
    )
}

private fun module(project: Project): Map<String, Any?> = buildMap {
    put("kotlin", project.tasks.withType(KotlinCompilationTask::class.java).sortedBy { it.name }.associate { task ->
        val options = task.compilerOptions
        task.name to mapOf(
            "allWarningsAsErrors" to options.allWarningsAsErrors.get(),
            "suppressWarnings" to options.suppressWarnings.get(),
            "progressiveMode" to options.progressiveMode.get(),
            "optIn" to options.optIn.get().sorted(),
            "freeCompilerArgs" to options.freeCompilerArgs.get(),
            "languageVersion" to options.languageVersion.orNull?.version,
            "apiVersion" to options.apiVersion.orNull?.version,
            "jvmTarget" to (options as? KotlinJvmCompilerOptions)?.jvmTarget?.get()?.target,
        )
    })
    project.extensions.findByType(ApplicationExtension::class.java)?.let { android ->
        put("android", mapOf(
            "compileSdk" to android.compileSdk, "compileSdkMinor" to android.compileSdkMinor,
            "minSdk" to android.defaultConfig.minSdk, "targetSdk" to android.defaultConfig.targetSdk,
            "lint" to lint(android.lint),
            "release" to android.buildTypes.getByName("release").let {
                mapOf("minify" to it.isMinifyEnabled, "shrinkResources" to it.isShrinkResources,
                    "proguardFiles" to it.proguardFiles.map { file -> file.name }, "debuggable" to it.isDebuggable)
            },
        ))
    }
    project.extensions.findByType(LibraryExtension::class.java)?.let { android ->
        put("android", mapOf(
            "compileSdk" to android.compileSdk, "compileSdkMinor" to android.compileSdkMinor,
            "minSdk" to android.defaultConfig.minSdk, "lint" to lint(android.lint),
        ))
    }
    project.extensions.findByType(TestExtension::class.java)?.let { android ->
        put("android", mapOf(
            "compileSdk" to android.compileSdk, "compileSdkMinor" to android.compileSdkMinor,
            "minSdk" to android.defaultConfig.minSdk, "targetSdk" to android.defaultConfig.targetSdk,
        ))
    }
    put("detekt", project.tasks.withType(Detekt::class.java).sortedBy { it.name }.associate { task ->
        task.name to mapOf(
            "ignoreFailures" to task.ignoreFailures.get(),
            "config" to task.config.files.map { it.relativeTo(project.rootDir).invariantSeparatorsPath }.sorted(),
            "buildUponDefaultConfig" to task.buildUponDefaultConfig.get(),
            "allRules" to task.allRules.get(),
            "disableDefaultRuleSets" to task.disableDefaultRuleSets.get(),
            "autoCorrect" to task.autoCorrect.get(),
            "baseline" to task.baseline.orNull?.asFile?.name,
            "failOnSeverity" to task.failOnSeverity.orNull?.name,
        )
    })
    put("tests", project.tasks.withType(Test::class.java).sortedBy { it.name }.associate { task ->
        task.name to mapOf(
            "ignoreFailures" to task.ignoreFailures,
            "include" to task.filter.includePatterns.sorted(),
            "exclude" to task.filter.excludePatterns.sorted(),
            "includes" to task.includes.sorted(),
            "excludes" to task.excludes.sorted(),
            "failOnNoMatchingTests" to task.filter.isFailOnNoMatchingTests,
        )
    })
}

private fun lint(lint: Lint): Map<String, Any?> = mapOf(
    "checkOnly" to lint.checkOnly.sorted(), "error" to lint.error.sorted(), "disable" to lint.disable.sorted(),
    "enable" to lint.enable.sorted(), "abortOnError" to lint.abortOnError, "warningsAsErrors" to lint.warningsAsErrors,
    "ignoreWarnings" to lint.ignoreWarnings, "checkTestSources" to lint.checkTestSources,
    "baseline" to lint.baseline?.name, "lintConfig" to lint.lintConfig?.name,
)
