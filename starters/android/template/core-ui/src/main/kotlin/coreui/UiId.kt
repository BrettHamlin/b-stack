package coreui

import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import core.UiId

/** Tags an element with its typed identifier, so journeys can find it (as a resource id, through UiAutomator). */
fun Modifier.uiId(id: UiId): Modifier = semantics { testTagsAsResourceId = true }.testTag(id.value)
