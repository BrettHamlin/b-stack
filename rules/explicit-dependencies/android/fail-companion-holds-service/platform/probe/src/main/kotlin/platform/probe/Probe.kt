package platform.probe

class Http(val base: String)

class Repository(private val http: Http) {
    companion object {
        val shared = Repository(Http("https://example.com"))
    }
}
