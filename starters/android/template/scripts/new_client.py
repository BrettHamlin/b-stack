"""Give a feature a client that keeps data (a store), the way the module shape expects, wired into both apps.

  features/<feature>/api   <Feature><Name>: the client interface; <Feature><Name>Result, what a call gives back (Done,
                           Failed, Unreadable); <Feature><Name>Data, what it keeps (@Serializable, saved as JSON)
  platform/<name>          File<Feature><Name>, the real client (JSON in the app's files folder), and its test
  features/<feature>/logic/src/commonTest   Memory<Feature><Name>, a fake for the model's tests (failing, unreadable)
  fixtures                 <Feature><Name>Setup (Empty, FailingSaves, Unreadable), the client for a setup, and which
                           setup each Fixture runs on
  app, app-verify          the client in each Application class (app: the real one; app-verify: the fixture's, made
                           once per process), and the module links (`uses`) this needs

Everything passes every gate as created. Then pass the client to the feature's model (the apps build it with
rememberModel), write the model's tests with the fake, and add a Fixture for each setup a journey needs (the compiler
makes <feature><Name>Setup say which setup it runs on). For a client that does something other than keep data (a sound,
a clock), change the interface and the fakes to match, keeping the same places.

Usage: python3 scripts/new_client.py <feature> <name>   (<feature>: an existing features/<feature>; <name>: lowercase
                                                          letters and digits, the platform module, such as `store`)
"""
from pathlib import Path
import json
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify import without_comments  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r'^[a-z][a-z0-9]{0,29}$')
APPLICATION = re.compile(r'\bclass\s+(\w+)\s*:\s*Application\s*\(\s*\)')
FIXTURE_ENUM = re.compile(r'\benum\s+class\s+Fixture\b[^{]*\{')


def cap(word: str) -> str:
    return word[0].upper() + word[1:]


def api_file(f: str, client: str) -> str:
    return f'''package {f}.api

import kotlinx.serialization.Serializable

/** What [{client}] keeps, saved as JSON (kotlinx.serialization). Replace the placeholder with the data's fields; give a
 * field added later a default, so what an older version saved still loads. */
@Serializable
data class {client}Data(val version: Int = 1)

/** What a [{client}] call gives back. */
sealed interface {client}Result<out T> {{
    data class Done<T>(val value: T) : {client}Result<T>

    /** The storage failed (a full disk, a missing folder): nothing was read or written. */
    data object Failed : {client}Result<Nothing>

    /** What's stored can't be read (not this data, or a format this version doesn't know). Never overwrite it unasked. */
    data object Unreadable : {client}Result<Nothing>
}}

/** Where the {f} feature keeps its data. A platform module implements it; the composition roots pass it to the model. */
interface {client} {{
    /** What's stored, or null if nothing is yet. */
    suspend fun load(): {client}Result<{client}Data?>

    suspend fun save(data: {client}Data): {client}Result<Unit>
}}
'''


def platform_file(f: str, name: str, client: str, filename: str) -> str:
    return f'''package platform.{name}

import android.content.Context
import {f}.api.{client}
import {f}.api.{client}Data
import {f}.api.{client}Result
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import java.io.File
import java.io.IOException

/** Keeps {client}Data in [file] as JSON. A save writes a new file and renames it into place, so a failed save leaves
 * what was there; saves take turns, so two at once never share the new file. File work runs on [io]. */
class File{client}(private val file: File, private val io: CoroutineDispatcher) : {client} {{
    /** The client on the app's own files folder. */
    constructor(context: Context, io: CoroutineDispatcher) : this(File(context.filesDir, "{filename}"), io)

    private val writing = Mutex()

    override suspend fun load(): {client}Result<{client}Data?> = withContext(io) {{
        try {{
            if (!file.exists()) return@withContext {client}Result.Done(null)
            {client}Result.Done(json.decodeFromString({client}Data.serializer(), file.readText()))
        }} catch (_: IllegalArgumentException) {{
            {client}Result.Unreadable // not JSON, or not this data (kotlinx.serialization's SerializationException is one)
        }} catch (_: IOException) {{
            {client}Result.Failed
        }}
    }}

    override suspend fun save(data: {client}Data): {client}Result<Unit> = writing.withLock {{ write(data) }}

    private suspend fun write(data: {client}Data): {client}Result<Unit> = withContext(io) {{
        try {{
            val staged = File(file.parentFile, "${{file.name}}.new")
            staged.writeText(json.encodeToString({client}Data.serializer(), data))
            if (staged.renameTo(file)) {client}Result.Done(Unit) else {client}Result.Failed
        }} catch (_: IOException) {{
            {client}Result.Failed
        }}
    }}
}}

/** Fields a newer version added are skipped, so going back a version still loads what it saved. */
private val json = Json {{ ignoreUnknownKeys = true }}
'''


def platform_test(f: str, name: str, client: str, filename: str) -> str:
    return f'''package platform.{name}

import {f}.api.{client}Data
import {f}.api.{client}Result
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.runTest
import java.io.File
import java.nio.file.Files
import kotlin.test.Test
import kotlin.test.assertEquals

class File{client}Test {{
    private val folder = Files.createTempDirectory("{filename}").toFile()
    private val file = File(folder, "{filename}")
    private val client = File{client}(file, Dispatchers.Unconfined)

    @Test
    fun nothingStoredLoadsAsNothing() = runTest {{
        assertEquals({client}Result.Done(null), client.load())
    }}

    @Test
    fun savedDataLoadsBack() = runTest {{
        val data = {client}Data()
        assertEquals({client}Result.Done(Unit), client.save(data))
        assertEquals({client}Result.Done(data), client.load())
    }}

    @Test
    fun dataItCantReadIsUnreadable() = runTest {{
        file.writeText("not {client}Data")
        assertEquals({client}Result.Unreadable, client.load())
    }}

    @Test
    fun aSaveThatCantBeWrittenFails() = runTest {{
        val missing = File{client}(File(folder, "missing/{filename}"), Dispatchers.Unconfined)
        assertEquals({client}Result.Failed, missing.save({client}Data()))
    }}
}}
'''


def fake_file(f: str, client: str) -> str:
    return f'''package {f}.logic

import {f}.api.{client}
import {f}.api.{client}Data
import {f}.api.{client}Result

/** A {client} in memory, for the model's tests: [failing] makes every call fail, [unreadable] every load. */
class Memory{client}(
    private var stored: {client}Data? = null,
    private val failing: Boolean = false,
    private val unreadable: Boolean = false,
) : {client} {{
    val current: {client}Data? get() = stored

    override suspend fun load(): {client}Result<{client}Data?> = when {{
        failing -> {client}Result.Failed
        unreadable -> {client}Result.Unreadable
        else -> {client}Result.Done(stored)
    }}

    override suspend fun save(data: {client}Data): {client}Result<Unit> {{
        if (failing) return {client}Result.Failed
        stored = data
        return {client}Result.Done(Unit)
    }}
}}
'''


def fixtures_file(f: str, name: str, client: str, filename: str, fixtures: list[str]) -> str:
    lower = client[0].lower() + client[1:]
    cases = ''.join(f'    Fixture.{c} -> {client}Setup.Empty\n' for c in fixtures)
    return f'''package fixtures

import android.content.Context
import {f}.api.{client}
import {f}.api.{client}Data
import {f}.api.{client}Result
import kotlinx.coroutines.CoroutineDispatcher
import platform.{name}.File{client}
import java.io.File

/** What the {f} feature's {client} holds when a journey starts, and how it behaves. */
enum class {client}Setup {{
    /** Nothing stored yet, on the real client. */
    Empty,

    /** Nothing stored, on the real client, except every save fails. */
    FailingSaves,

    /** Stored data the client can't read. */
    Unreadable,
}}

/** The setup each fixture runs {client} on: a new Fixture must say which (the compiler makes it). */
fun {lower}Setup(fixture: Fixture): {client}Setup = when (fixture) {{
{cases}}}

/** The {client} for [setup], in the app's files folder. With [reset], it starts from the setup's data; without it (a
 * relaunch), it keeps what the last launch saved. */
fun {lower}(setup: {client}Setup, context: Context, io: CoroutineDispatcher, reset: Boolean): {client} {{
    val dir = File(context.filesDir, "fixture-{filename.removesuffix('.json')}")
    val file = File(dir, "{filename}")
    if (reset) {{
        dir.deleteRecursively()
        dir.mkdirs()
        when (setup) {{
            {client}Setup.Empty, {client}Setup.FailingSaves -> Unit
            {client}Setup.Unreadable -> file.writeText("not {client}Data")
        }}
    }}
    val real = File{client}(file, io)
    return when (setup) {{
        {client}Setup.Empty, {client}Setup.Unreadable -> real
        {client}Setup.FailingSaves -> FailingSaves{client}(real)
    }}
}}

private class FailingSaves{client}(private val real: {client}) : {client} {{
    override suspend fun load(): {client}Result<{client}Data?> = real.load()

    override suspend fun save(data: {client}Data): {client}Result<Unit> = {client}Result.Failed
}}
'''


def app_members(client: str, name: str) -> str:
    lower = client[0].lower() + client[1:]
    return f'    val {lower}: {client} by lazy {{ File{client}(this, Dispatchers.IO) }}\n'


def verify_members(client: str) -> str:
    lower = client[0].lower() + client[1:]
    return f'''    private var {lower}InUse: {client}? = null

    /** The {client} for [fixture], made once per process as in the shipped app; with [reset], its data starts from
     * the fixture's (test setup, so it may write here). */
    fun {lower}(fixture: Fixture, reset: Boolean): {client} = {lower}InUse ?: run {{
        val policy = StrictMode.allowThreadDiskWrites()
        try {{
            {lower}({lower}Setup(fixture), this, Dispatchers.IO, reset).also {{ {lower}InUse = it }}
        }} finally {{
            StrictMode.setThreadPolicy(policy)
        }}
    }}
'''


code = without_comments


def fixture_cases() -> tuple[list[str] | None, str]:
    for path in sorted((ROOT / 'fixtures/src/main/kotlin').rglob('*.kt')):
        text = code(path.read_text())
        match = FIXTURE_ENUM.search(text)
        if not match:
            continue
        body = text[match.end():]
        return [re.match(r'\s*(?:@\w+\s*)*(\w+)', part).group(1) for part in top_level(body) if part.strip()], \
            str(path.relative_to(ROOT))
    return None, ''


def top_level(body: str) -> list[str]:
    """An enum body's entries: split at commas outside brackets, up to the `;` or `}` that ends them."""
    parts, depth, start = [], 0, 0
    for i, c in enumerate(body):
        if c in '([{':
            depth += 1
        elif c in ')]' or (c == '}' and depth):
            depth -= 1
        elif depth == 0 and c in ',;}':
            parts.append(body[start:i])
            start = i + 1
            if c != ',':
                return parts
    return parts + [body[start:]]


def with_imports(text: str, imports: list[str]) -> str:
    lines = text.split('\n')
    have = [i for i, line in enumerate(lines) if line.startswith('import ')]
    wanted = sorted(set([lines[i] for i in have] + [f'import {i}' for i in imports]))
    if have:
        return '\n'.join(lines[:have[0]] + wanted + lines[have[-1] + 1:])
    package = next(i for i, line in enumerate(lines) if line.startswith('package '))
    return '\n'.join(lines[:package + 1] + [''] + wanted + lines[package + 1:])


def header_end(text: str, start: int) -> tuple[int, bool] | None:
    """Where the class header that continues at [start] (after `Application()`) ends, and whether a body `{` opens
    there: the rest of the supertype list is skipped bracket by bracket. None if the brackets don't balance."""
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c in '(<':
            depth += 1
        elif c in ')>':
            depth -= 1
            if depth < 0:
                return None
        elif depth == 0 and c == '{':
            return i + 1, True
        elif depth == 0 and c == '\n':
            continued = text[start:i].rstrip().endswith(',') or text[i:].lstrip().startswith(('{', ','))
            if not continued:
                return len(text[:i].rstrip()), False
    return (len(text.rstrip()), False) if depth == 0 else None


def with_members(text: str, members: str) -> str | None:
    match = APPLICATION.search(code(text))
    header = header_end(code(text), match.end()) if match else None
    if header is None:
        return None
    end, body = header
    if body:
        rest = text[end:].lstrip(' \n')
        return text[:end] + '\n' + members + ('' if rest.startswith('}') else '\n    ') + rest
    return text[:end].rstrip() + ' {\n' + members + '}' + text[end:]


def application(module: str) -> Path | None:
    for path in sorted((ROOT / module / 'src/main/kotlin').rglob('*.kt')):
        if APPLICATION.search(code(path.read_text())):
            return path
    return None


def linked(module: str, add: list[str]) -> str | None:
    path = ROOT / module / 'module.toml'
    text = path.read_text() if path.is_file() else 'uses = []\n'
    match = re.search(r'^\s*uses\s*=\s*\[(.*?)\]', text, re.MULTILINE | re.DOTALL)
    if not match:
        return None
    uses = re.findall(r'"([^"]+)"', match.group(1))
    uses += [u for u in add if u not in uses]
    return text[:match.start()] + 'uses = [' + ', '.join(f'"{u}"' for u in uses) + ']' + text[match.end():]


def shape_allows() -> list[str]:
    """Links this command adds that arch/shape.json doesn't allow, as `<role> may not use <role>`."""
    roles = json.loads((ROOT / 'arch/shape.json').read_text())['roles']
    needs = [('platform', 'api'), ('fixtures', 'api'), ('fixtures', 'platform'), ('app', 'platform')]
    return [f'a {a} module may not use {b}' for a, b in needs
            if not any(entry.removesuffix('(own)') == b for entry in roles.get(a, {}).get('may_use', []))]


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not all(NAME.match(a) for a in argv):
        print(__doc__, file=sys.stderr)
        return 2
    f, name = argv
    Feature, client = cap(f), cap(f) + cap(name)
    lower = client[0].lower() + client[1:]
    filename = f'{f}-{name}.json'
    problems = []
    if not (ROOT / 'features' / f / 'api').is_dir():
        problems.append(f'features/{f}/api isn\'t a feature\'s api module. Start the feature with '
                        f'python3 scripts/new_feature.py {f}.')
    problems += [f'arch/shape.json: {p}, so the client can\'t be wired. Stop and report.' for p in shape_allows()]
    cases, enum_path = fixture_cases()
    if cases is None:
        problems.append('fixtures has no `enum class Fixture { ... }` (the test-mode setups journeys launch with).')
    apps = {module: application(module) for module in ('app', 'app-verify')}
    problems += [f'{m}/src/main/kotlin has no `class <Name> : Application()` to wire the client into.'
                 for m, path in apps.items() if path is None]
    if problems:
        print('Not created: ' + '\n'.join(problems), file=sys.stderr)
        return 1
    planned = {
        Path(f'features/{f}/api/src/commonMain/kotlin/{f}/api/{client}.kt'): api_file(f, client),
        Path(f'platform/{name}/src/main/kotlin/platform/{name}/File{client}.kt'): platform_file(f, name, client, filename),
        Path(f'platform/{name}/src/test/kotlin/platform/{name}/File{client}Test.kt'): platform_test(f, name, client, filename),
        Path(f'features/{f}/logic/src/commonTest/kotlin/{f}/logic/Memory{client}.kt'): fake_file(f, client),
        Path(f'fixtures/src/main/kotlin/fixtures/{client}Fixtures.kt'): fixtures_file(f, name, client, filename, cases),
    }
    taken = [str(p) for p in planned if (ROOT / p).exists()]
    declared = re.compile(rf'\b(?:class|interface|object|typealias)\s+({client}(?:Data|Result|Setup)?|File{client}|Memory{client})\b')
    member = re.compile(rf'\b(?:val|var|fun)\s+{lower}(?:Setup|InUse)?\b')
    for source in sorted(ROOT.glob('**/src/**/*.kt')):
        if '.build' in source.parts:
            continue
        text = code(source.read_text())
        found = declared.findall(text) + (member.findall(text) if source in apps.values() else [])
        taken += [f'{source.relative_to(ROOT)} (it declares {", ".join(dict.fromkeys(found))})'] if found else []
    if taken:
        print(f'Not created: {", ".join(taken)} already exist.', file=sys.stderr)
        return 1
    links = {f'platform/{name}': ['core', f'features/{f}/api'], 'fixtures': [f'features/{f}/api', f'platform/{name}'],
             'app': [f'features/{f}/api', f'platform/{name}'], 'app-verify': [f'features/{f}/api']}
    edits = {Path(m) / 'module.toml': linked(m, add) for m, add in links.items()}
    edits = {p: text for p, text in edits.items() if text is None or not (ROOT / p).is_file() or (ROOT / p).read_text() != text}
    unreadable = [str(p) for p, text in edits.items() if text is None]
    app_text = with_members(apps['app'].read_text(), app_members(client, name))
    verify_text = with_members(apps['app-verify'].read_text(), verify_members(client))
    if unreadable or app_text is None or verify_text is None:
        bad = [f'{p} has no `uses = [...]` list' for p in unreadable] + [
            f'{apps[m].relative_to(ROOT)}: can\'t read the class header after `Application()`'
            for m, text in (('app', app_text), ('app-verify', verify_text)) if text is None]
        print(f'Not created: {"; ".join(bad)}.', file=sys.stderr)
        return 1
    edits[apps['app'].relative_to(ROOT)] = with_imports(
        app_text, [f'{f}.api.{client}', 'kotlinx.coroutines.Dispatchers', f'platform.{name}.File{client}'])
    edits[apps['app-verify'].relative_to(ROOT)] = with_imports(
        verify_text, ['android.os.StrictMode', f'{f}.api.{client}', 'fixtures.Fixture', f'fixtures.{lower}',
                      f'fixtures.{lower}Setup', 'kotlinx.coroutines.Dispatchers'])
    planned.update({p: text for p, text in edits.items() if not (ROOT / p).exists()})
    edits = {p: text for p, text in edits.items() if p not in planned}
    for path, text in {**planned, **edits}.items():
        (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / path).write_text(text)
    print('\n'.join(f'created {p}' for p in planned))
    print('\n'.join(f'updated {p}' for p in edits))
    print(f'Next: pass the client to the {f} model where each app\'s Activity builds it, e.g. in app\n'
          f'  rememberModel("{f}") {{ scope, saved -> {Feature}Model(services.{lower}, scope, saved) }}\n'
          f'and in app-verify with `app.{lower}(fixture, reset)`; write the model\'s tests with Memory{client}; add a '
          f'Fixture ({enum_path}) for each {client}Setup a journey needs, mapped in {lower}Setup; then run '
          'python3 scripts/check.py.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
