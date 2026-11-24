package platform.probe

class Worker(private val work: () -> Unit) : Thread() {
    override fun run() = work()
}
