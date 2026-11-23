package platform.probe

class Http(val base: String)

object Services {
    val http get() = Http("https://example.com")
}
