package platform.probe

class Http(val base: String) {
    val status: Int = 200
}

sealed interface Link {
    val online: Boolean
}

data object Live : Link {
    override val online get() = Http("https://example.com").status == 200
}
