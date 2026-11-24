package platform.probe

class Settings {
    fun longestName(): Int {
        var longest = 0
        for (name in System.getProperties().stringPropertyNames()) longest = maxOf(longest, name.length)
        return longest
    }
}
