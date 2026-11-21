public let features: [Feature] = [
    Feature("Settings", links: [.logicUsesCore, .viewUsesCore, .platformImplementsInterface, .fixturesUseInterface]),
    Feature("Profile", links: [.viewUsesCore, .platformImplementsInterface, .fixturesUseInterface]),
]

public let sharedLinks: Set<SharedLink> = [.platformUsesCore, .fixturesUseCore, .fixturesUsePlatform, .appUsesPlatform]
