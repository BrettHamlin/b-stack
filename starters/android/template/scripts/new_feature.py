"""Create a feature the way the module shape expects: its three modules, its feature-map entry and a journey to write.

  features/<name>/api     <Name>Ui, the feature's UI identifiers (only an api module can declare a UiId)
  features/<name>/logic   <Name>Model: state as a StateFlow, send(action), work in the scope it's given, the session
                          that isn't stored (half-done input) in its Saved; and a test to write
  features/<name>/ui      <Name>Route(model), the entry point both apps show, and the screen
  feature-map/<name>.toml the feature and its first journey, <name>Works
  verify/journeys/.../<Name>Journeys.kt   that journey (it turns the device and has the process end, as the map
                          check requires), and the runner's adapters, regenerated
  module.toml links       verify/journeys uses the feature's api; app and app-verify use its api, logic and ui

Everything compiles and passes detekt, Lint, Konsist, arch and deps as created. The logic test and the journey fail
until you write them, with a message saying so: a feature isn't done until both prove it works. The apps don't show
the feature until you add its entry point to each (app/ and app-verify/):
  <Name>Route(rememberModel("<name>") { scope, saved -> <Name>Model(scope, saved) })
Then run python3 scripts/check.py.

When the feature's code goes in a module another feature already has (a new rule of the same screen, such as a
board game's combat in its `battle` module), don't make new modules: give it its own map entry and journey in that
module with --in:
  feature-map/<id>.toml   the feature, naming the existing module, and its first journey, <id>Works
  verify/journeys/.../<Id>Journeys.kt   that journey (turns the device, has the process end), and the adapters
  features/<module>/logic/src/commonTest/.../<Id>Test.kt   a test to write, in the module's logic
Both fail until you write them, as above.

Usage: python3 scripts/new_feature.py <name>      (lowercase letters and digits, starting with a letter: a Kotlin
                                                   package name, such as `notes`)
       python3 scripts/new_feature.py <id> --in <module>   (<id>: lowercase words joined by `-`, such as `undo-move`;
                                                   <module>: an existing features/<module>)
"""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify import ADAPTERS, JOURNEYS, adapters_text, journeys_in_code, ui_ids  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r'^[a-z][a-z0-9]{0,29}$')
FEATURE_ID = re.compile(r'^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$')
KOTLIN = {'as', 'break', 'class', 'continue', 'do', 'else', 'false', 'for', 'fun', 'if', 'in', 'interface', 'is',
          'null', 'object', 'package', 'return', 'super', 'this', 'throw', 'true', 'try', 'typealias', 'typeof', 'val',
          'var', 'when', 'while'}


def files(name: str) -> dict[Path, str]:
    Name = name[0].upper() + name[1:]
    feature = Path('features') / name
    return {
        feature / 'api/module.toml': 'uses = ["core"]\n',
        feature / f'api/src/commonMain/kotlin/{name}/api/{Name}Ui.kt': f'''package {name}.api

import core.UiId

/** The {name} screen's elements, tagged by the view (Modifier.uiId) and found by journeys. */
object {Name}Ui {{
    val title = UiId("{name}.title")
}}
''',
        feature / 'logic/module.toml': f'uses = ["core", "features/{name}/api"]\n',
        feature / f'logic/src/commonMain/kotlin/{name}/logic/{Name}Model.kt': f'''package {name}.logic

import core.Saved
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

/** What the {name} screen shows. */
data class {Name}State(val title: String = "{Name}")

sealed interface {Name}Action {{
    data class TitleChanged(val text: String) : {Name}Action
}}

/** The {name} screen's state. The view renders [state] and sends actions; clients the feature needs (interfaces in its
 * api module, implemented in a platform module) are passed in here by the apps. Work runs in [scope], which the
 * composition root owns, and half-done input goes in [saved], so it survives the process ending in the background. */
class {Name}Model(private val scope: CoroutineScope, private val saved: Saved) {{
    private val current = MutableStateFlow({Name}State(title = saved[TITLE] ?: "{Name}"))
    val state: StateFlow<{Name}State> = current.asStateFlow()

    fun send(action: {Name}Action) {{
        when (action) {{
            is {Name}Action.TitleChanged -> {{
                saved[TITLE] = action.text
                current.update {{ it.copy(title = action.text) }}
            }}
        }}
    }}
}}

private const val TITLE = "title"
''',
        feature / f'logic/src/commonTest/kotlin/{name}/logic/{Name}ModelTest.kt': f'''package {name}.logic

import kotlin.test.Test
import kotlin.test.fail

class {Name}ModelTest {{
    @Test
    fun {name}Works() {{
        fail("Write this test: the {name} model's behaviour, every state asserted whole with Turbine (see the tally's tests).")
    }}
}}
''',
        feature / 'ui/module.toml': f'uses = ["core", "core-ui", "features/{name}/api", "features/{name}/logic"]\n',
        feature / f'ui/src/main/kotlin/{name}/ui/{Name}Screen.kt': f'''package {name}.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import coreui.uiId
import {name}.api.{Name}Ui
import {name}.logic.{Name}Action
import {name}.logic.{Name}Model
import {name}.logic.{Name}State

/** The {name} feature's entry point. Both apps call it with the model they built from their services. */
@Composable
fun {Name}Route(model: {Name}Model) {{
    val state by model.state.collectAsState()
    {Name}Screen(state, model::send)
}}

@Composable
fun {Name}Screen(state: {Name}State, send: ({Name}Action) -> Unit) {{
    Column(Modifier.fillMaxSize().safeDrawingPadding().padding(24.dp)) {{
        Text(state.title, modifier = Modifier.uiId({Name}Ui.title))
    }}
}}
''',
        Path(f'feature-map/{name}.toml'): f'''id = "{name}"
summary = "Write what the {name} feature does for the user."
modules = ["{name}"]

[[journeys]]
name = "{name}Works"
proves = "Write what this journey shows working in the app, including after the device turns and after the process ends in the background."
''',
        (JOURNEYS / f'journeys/{Name}Journeys.kt').relative_to(ROOT): f'''package journeys

import journeykit.Journey
import {name}.api.{Name}Ui

fun Journey.{name}Works() {{
    val screen = launch()
    screen.checkpoint("opened")
    screen.rotate()
    screen.returnAfterProcessDeath()
    screen.find({Name}Ui.title).shows(
        "Write this journey: use the {name} feature as a user would, check what they'd see, and that it survives the " +
            "device turning and the process ending.",
    )
}}
''',
    }


def files_in_module(fid: str, module: str, package: str, ui: str, element: str) -> dict[Path, str]:
    """A feature that lives in an existing module: its map entry, journey stub and logic test stub."""
    camel = fid.split('-')[0] + ''.join(w[:1].upper() + w[1:] for w in fid.split('-')[1:])
    Camel = camel[0].upper() + camel[1:]
    return {
        Path(f'feature-map/{fid}.toml'): f'''id = "{fid}"
summary = "Write what the {fid} feature does for the user."
modules = ["{module}"]

[[journeys]]
name = "{camel}Works"
proves = "Write what this journey shows working in the app, including after the device turns and after the process ends in the background."
''',
        (JOURNEYS / f'journeys/{Camel}Journeys.kt').relative_to(ROOT): f'''package journeys

import journeykit.Journey
import {package}.{ui}

fun Journey.{camel}Works() {{
    val screen = launch()
    screen.checkpoint("opened")
    screen.rotate()
    screen.returnAfterProcessDeath()
    screen.find({ui}.{element}).shows(
        "Write this journey: use the {fid} feature as a user would, check what they'd see, and that it survives the " +
            "device turning and the process ending.",
    )
}}
''',
        Path(f'features/{module}/logic/src/commonTest/kotlin/{module}/logic/{Camel}Test.kt'): f'''package {module}.logic

import kotlin.test.Test
import kotlin.test.fail

class {Camel}Test {{
    @Test
    fun {camel}Works() {{
        fail("Write this test: the {fid} feature's behaviour in the model, every state asserted whole with Turbine.")
    }}
}}
''',
    }


def add_in_module(fid: str, module: str) -> int:
    if not (ROOT / 'features' / module / 'api').is_dir():
        found = sorted(p.name for p in (ROOT / 'features').iterdir() if p.is_dir()) if (ROOT / 'features').is_dir() else []
        print(f'Not created: features/{module} isn\'t a feature module (there are: {", ".join(found) or "none"}). '
              f'For a feature with modules of its own, run python3 scripts/new_feature.py <name>.', file=sys.stderr)
        return 1
    Module = module[0].upper() + module[1:]
    elements = [(where, obj, element) for where, obj, element in ui_ids() if where.startswith(f'features/{module}/api/')]
    if not elements:
        print(f'Not created: features/{module}/api declares no UiId (in a <Feature>Ui object) for the journey stub to '
              'find.', file=sys.stderr)
        return 1
    where, obj, element = elements[0]
    package = re.search(r'^\s*package\s+([\w.]+)', (ROOT / where).read_text(), re.MULTILINE)
    planned = files_in_module(fid, module, package.group(1) if package else f'{module}.api', obj, element)
    taken = [str(path) for path in planned if (ROOT / path).exists()]
    if taken:
        print(f'Not created: {", ".join(taken)} already exist.', file=sys.stderr)
        return 1
    for path, text in planned.items():
        (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / path).write_text(text)
    ADAPTERS.write_text(adapters_text(journeys_in_code()))
    print('\n'.join(f'created {path}' for path in planned))
    print(f'updated {ADAPTERS.relative_to(ROOT)}')
    print(f'Next: write the feature in features/{module} (its state and actions in {Module}Model), the test and the '
          'journey, and what the map entry says it does; then run python3 scripts/check.py.')
    return 0


LINKS = {'verify/journeys': ('api',), 'app': ('api', 'logic', 'ui'), 'app-verify': ('api', 'logic', 'ui')}


def linked(module: str, name: str, parts: tuple[str, ...]) -> str | None:
    """The module's module.toml with the feature's modules added to its `uses` list, or None if it has no such list."""
    text = (ROOT / module / 'module.toml').read_text()
    match = re.search(r'^\s*uses\s*=\s*\[(.*?)\]', text, re.MULTILINE | re.DOTALL)
    if not match:
        return None
    uses = re.findall(r'"([^"]+)"', match.group(1))
    uses += [f'features/{name}/{part}' for part in parts if f'features/{name}/{part}' not in uses]
    return text[:match.start()] + 'uses = [' + ', '.join(f'"{u}"' for u in uses) + ']' + text[match.end():]


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == '--in':
        if not FEATURE_ID.match(argv[0]) or not NAME.match(argv[2]):
            print(__doc__, file=sys.stderr)
            return 2
        return add_in_module(argv[0], argv[2])
    if len(argv) != 1 or not NAME.match(argv[0]) or argv[0] in KOTLIN:
        print(__doc__, file=sys.stderr)
        return 2
    name = argv[0]
    planned = files(name)
    taken = [str(path) for path in planned if (ROOT / path).exists()]
    if (ROOT / 'features' / name).exists():
        taken.insert(0, f'features/{name}')
    if taken:
        print(f'Not created: {", ".join(taken)} already exist.', file=sys.stderr)
        return 1
    links = {module: linked(module, name, parts) for module, parts in LINKS.items()}
    unreadable = [module for module, text in links.items() if text is None]
    if unreadable:
        print(f'Not created: {", ".join(f"{m}/module.toml" for m in unreadable)} has no `uses = [...]` list.',
              file=sys.stderr)
        return 1
    for path, text in planned.items():
        (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / path).write_text(text)
    for module, text in links.items():
        (ROOT / module / 'module.toml').write_text(text)
    ADAPTERS.write_text(adapters_text(journeys_in_code()))
    print('\n'.join(f'created {path}' for path in planned))
    print('\n'.join(f'updated {module}/module.toml' for module in LINKS))
    print(f'updated {ADAPTERS.relative_to(ROOT)}')
    Name = name[0].upper() + name[1:]
    print(f'Next: show the feature in both apps (app/ and app-verify/), e.g.\n'
          f'  {Name}Route(rememberModel("{name}") {{ scope, saved -> {Name}Model(scope, saved) }})\n'
          'then write the logic, the test and the journey, and run python3 scripts/check.py.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
