package platform.probe

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class Reader {
    suspend fun read(): String = withContext(Dispatchers.IO) { "data" }
}
