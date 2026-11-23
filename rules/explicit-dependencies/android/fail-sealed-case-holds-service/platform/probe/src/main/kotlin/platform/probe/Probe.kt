package platform.probe

class Http(val base: String)

sealed interface Environment {
    val http: Http
}

data object Production : Environment {
    override val http = Http("https://example.com")
}
