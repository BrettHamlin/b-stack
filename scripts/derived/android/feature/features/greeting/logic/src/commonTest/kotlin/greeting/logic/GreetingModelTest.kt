package greeting.logic

import app.cash.turbine.test
import core.SavedInMemory
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals

class GreetingModelTest {
    @Test
    fun titleChangesAndIsSaved() = runTest {
        val saved = SavedInMemory()
        val model = GreetingModel(backgroundScope, saved)
        model.state.test {
            assertEquals(GreetingState(), awaitItem())
            model.send(GreetingAction.TitleChanged("Hello"))
            assertEquals(GreetingState(title = "Hello"), awaitItem())
        }
        GreetingModel(backgroundScope, saved).state.test {
            assertEquals(GreetingState(title = "Hello"), awaitItem())
        }
    }
}
