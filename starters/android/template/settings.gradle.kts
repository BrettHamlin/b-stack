pluginManagement {
    includeBuild("build-logic")
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
plugins { id("bstack.settings") }

dependencyResolutionManagement {
    // Libraries come only from Google's and Maven Central's repositories; a module can't add its own.
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories { google(); mavenCentral() }
}

rootProject.name = "starter"
