package platform.probe

class Database(val name: String)

val database by lazy { Database("main") }
