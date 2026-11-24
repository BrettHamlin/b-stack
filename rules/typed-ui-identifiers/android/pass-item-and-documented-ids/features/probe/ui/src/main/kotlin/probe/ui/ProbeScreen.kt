package probe.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import coreui.uiId
import probe.api.ProbeUi

@Composable
fun Board(rows: Int, columns: Int) {
    Column {
        repeat(rows) { row ->
            Row { repeat(columns) { column -> Text("$row,$column", Modifier.uiId(ProbeUi.cell.at(row, column))) } }
        }
    }
}
