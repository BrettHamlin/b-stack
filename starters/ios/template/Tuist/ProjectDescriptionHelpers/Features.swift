// The app's features and the optional links they use. This is the file to edit when you add a feature or need a
// link: Project.swift builds every target from it and ModuleShape.swift. Only links inside the module shape can be
// written here (see FeatureLink and SharedLink); if you need one that isn't there, stop and report.

public let features: [Feature] = [
    Feature("Settings", links: [.logicUsesCore, .viewUsesCore, .platformImplementsInterface, .fixturesUseInterface]),
]

public let sharedLinks: Set<SharedLink> = [.platformUsesCore, .fixturesUseCore, .fixturesUsePlatform, .appUsesPlatform]
