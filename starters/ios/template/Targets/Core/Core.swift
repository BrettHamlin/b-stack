/// An accessibility identifier that views set and UI journeys find elements by.
///
/// It's its own type, not a String, so a journey can't pass a string where an identifier is expected: journeys find
/// elements through JourneyKit's `find(_ id: UIID)`. The initializer is `package`, and only Core and the `*Interface`
/// modules share the package name (Project.swift), so no other module can create a UIID in any form. A renamed or
/// invented identifier is then a compile error, not a journey that fails at run time.
public struct UIID: Hashable, Sendable, CustomStringConvertible {
    public let rawValue: String

    package init(_ rawValue: String) {
        self.rawValue = rawValue
    }

    public var description: String { rawValue }
}
