plugins { `kotlin-dsl` }

// Build output goes with the project's, into the cache folder (.build is a link there).
layout.buildDirectory.set(file("../.build/gradle/build-logic"))

dependencies {
    implementation(libs.android.gradle.plugin)
    implementation(libs.kotlin.gradle.plugin)
    implementation(libs.compose.gradle.plugin)
    implementation(libs.serialization.gradle.plugin)
    implementation(libs.detekt.gradle.plugin)
}

gradlePlugin {
    plugins {
        create("settings") { id = "bstack.settings"; implementationClass = "bstack.SettingsPlugin" }
        create("module") { id = "bstack.module"; implementationClass = "bstack.ModulePlugin" }
    }
}
