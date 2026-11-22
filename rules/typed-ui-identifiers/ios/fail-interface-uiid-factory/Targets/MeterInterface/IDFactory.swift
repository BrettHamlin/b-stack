public import Core

public enum IDFactory {
    public static func invented(_ raw: String) -> UIID {
        UIID(raw)
    }
}
