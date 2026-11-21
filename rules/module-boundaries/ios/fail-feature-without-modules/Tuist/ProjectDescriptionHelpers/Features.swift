public let features: [Feature] = [
    Feature("Settings", links: [.logicUsesCore, .viewUsesCore, .platformImplementsInterface, .fixturesUseInterface]),
    Feature("Profile"),
]

public let sharedLinks: Set<SharedLink> = [.platformUsesCore, .fixturesUseCore, .fixturesUsePlatform, .appUsesPlatform]
