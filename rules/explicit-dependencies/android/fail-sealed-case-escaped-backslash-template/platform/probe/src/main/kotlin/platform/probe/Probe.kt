package platform.probe

class Http(val base: String)

sealed interface Link {
    val base: String
}

data object Live : Link {
    override val base = "\\${Http("https://example.com").base}"
}
