package platform.probe

class Counter {
    private var count = 0

    fun bump() {
        Thread { synchronized(this) { count++ } }.start()
    }
}
