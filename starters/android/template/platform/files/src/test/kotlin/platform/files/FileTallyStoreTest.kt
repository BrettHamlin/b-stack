package platform.files

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.runTest
import tally.api.ItemName
import tally.api.Stored
import tally.api.Tally
import java.io.File
import java.nio.file.Files
import kotlin.test.Test
import kotlin.test.assertEquals

class FileTallyStoreTest {
    private val apple = ItemName.parse("apple") ?: error("valid name")

    @Test
    fun savedTallyLoadsBack() = runTest {
        val dir = Files.createTempDirectory("tally").toFile()
        val store = FileTallyStore(File(dir, "tally.json"), Dispatchers.Unconfined)
        assertEquals(Stored.Done(Tally.Empty), store.load())
        assertEquals(Stored.Done(Unit), store.save(Tally(mapOf(apple to 3))))
        assertEquals(Stored.Done(Tally(mapOf(apple to 3))), store.load())
    }

    @Test
    fun saveIntoAMissingFolderFailsAndKeepsNothing() = runTest {
        val dir = File(Files.createTempDirectory("tally").toFile(), "missing")
        val store = FileTallyStore(File(dir, "tally.json"), Dispatchers.Unconfined)
        assertEquals(Stored.Failed, store.save(Tally(mapOf(apple to 1))))
        assertEquals(Stored.Done(Tally.Empty), store.load())
    }

    @Test
    fun aFileThatIsntATallyFailsToLoad() = runTest {
        val dir = Files.createTempDirectory("tally").toFile()
        val file = File(dir, "tally.json")
        val store = FileTallyStore(file, Dispatchers.Unconfined)
        for (text in listOf("not a tally", """{"counts":{"two words":1}}""", """{"counts":{"apple":0}}""")) {
            file.writeText(text)
            assertEquals(Stored.Failed, store.load(), text)
        }
    }
}
