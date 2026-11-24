package bstack

import org.gradle.api.Plugin
import org.gradle.api.initialization.Settings

/** Includes every module folder in arch/shape.json, so a new module in a role's folder is built and checked
 * without editing a protected file. */
class SettingsPlugin : Plugin<Settings> {
    override fun apply(settings: Settings) {
        val root = settings.settingsDir
        Shape.load(root).modules(root).forEach { (folder, _) -> settings.include(":" + folder.replace('/', ':')) }
        settings.gradle.beforeProject {
            if (this == rootProject) {
                layout.buildDirectory.set(root.resolve(".build/gradle/root"))
                registerSettingsDump(this)
            } else {
                pluginManager.apply(ModulePlugin::class.java)
            }
        }
    }
}
