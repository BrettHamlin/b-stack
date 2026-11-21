public import Core

extension UIID: @retroactive ExpressibleByStringLiteral {
    public init(stringLiteral value: String) {
        self.init(value)
    }
}
