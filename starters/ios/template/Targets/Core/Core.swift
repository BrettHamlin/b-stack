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

    package init(indexing base: UIID, by indices: [Int]) {
        rawValue = base.rawValue + indices.map { ".\($0)" }.joined()
    }

    /// One identifier per item of a grid or list, built from a feature's constant: `BoardUIID.cell.at(3, 5)` is
    /// "board.cell.3.5". Only integers can be appended, so a String still can't become an identifier.
    public func at(_ indices: Int...) -> UIID {
        at(indices)
    }

    public func at(_ indices: [Int]) -> UIID {
        UIID(indexing: self, by: indices)
    }

    public var description: String { rawValue }
}
