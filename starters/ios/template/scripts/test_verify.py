"""Simulator-free checks for journey discovery, adapter integrity and isolated test plans."""
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch

import verify
from paths import cache_root


class VerifyContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=cache_root())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.addCleanup(patch.stopall)
        patch.object(verify, 'ROOT', self.root).start()
        patch.object(verify, 'DERIVED', self.root / 'DerivedData').start()
        # No test in this file may invoke xcrun, xcodebuild or any other external process.
        patch.object(verify.subprocess, 'run', side_effect=AssertionError('external process')).start()

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        return target

    def test_bodies_and_inherited_methods_are_discovered(self):
        self.write('Targets/AppVerifyJourneys/Body.swift', '''
            public class Base: Journey { public func testInherited() {} }
            public final class SettingsJourneys: Base {
                // A fake declaration with braces: class Hidden: Journey { func testHidden() {} }
                let text = #"quote: " }"#
                enum Checkpoint { case start }
                public func testVisible() {}
            }
        ''')
        self.assertEqual(verify.journeys_in_code(bodies_only=True), {
            'Base/testInherited', 'SettingsJourneys/testInherited', 'SettingsJourneys/testVisible',
        })
        generated = verify.adapters_source()
        self.assertIn('final class SettingsJourneys: XCTestCase', generated)
        self.assertIn('AppVerifyJourneys.SettingsJourneys(test: self).testInherited()', generated)
        self.assertNotIn('testHidden', generated)

    def test_adapter_drift_and_extra_files_are_rejected(self):
        self.write('Targets/AppVerifyJourneys/Body.swift', 'public class SettingsJourneys: Journey { public func testA() {} }')
        generated = self.write('Targets/AppVerifyUITests/GeneratedJourneys.swift', verify.adapters_source())
        self.assertEqual(verify.check_adapters(), [])
        generated.write_text(generated.read_text().replace('.testA()', '.testOther()'))
        self.assertIn('XCTest adapters differ', verify.check_adapters()[0])
        generated.write_text(verify.adapters_source())
        for name in ('Escape.swift', 'Escape.m'):
            extra = self.write(f'Targets/AppVerifyUITests/Nested/{name}', '// handwritten runner source')
            self.assertIn('XCTest adapters differ', verify.check_adapters()[0])
            extra.unlink()

    def test_unmapped_bodies_cannot_hide_behind_adapters(self):
        self.write('Targets/AppVerifyJourneys/Body.swift', 'public class NewJourneys: Journey { public func testA() {} }')
        self.write('Targets/AppVerifyUITests/GeneratedJourneys.swift', verify.adapters_source())
        _, errors = verify.check_map()
        self.assertIn('journey NewJourneys/testA is not in the feature map. Name it under the feature it proves.', errors)

    def test_missing_mapped_method_is_not_fabricated_by_generation(self):
        self.write('Targets/SettingsInterface/IDs.swift', '')
        self.write('Targets/Fixtures/Fixture.swift', 'enum Fixture {\ncase standard\n}')
        self.write('Targets/AppVerifyJourneys/Body.swift', 'public class SettingsJourneys: Journey { public func testA() {} }')
        self.write('Targets/AppVerifyUITests/GeneratedJourneys.swift', verify.adapters_source())
        self.write('feature-map/settings.toml', '''id = "settings"
module = "Settings"
summary = "Settings"
entry_points = ["Launch"]
[[journeys]]
test = "SettingsJourneys/testA"
fixture = "standard"
proves = "Existing test"
[[journeys]]
test = "SettingsJourneys/testMissing"
fixture = "standard"
proves = "Must remain absent in results"
''')
        self.assertEqual(verify.check_map()[1], [])
        self.assertNotIn('testMissing', verify.adapters_source())

    def test_isolation_preserves_embedded_test_bundle_and_sdk_paths(self):
        products = verify.DERIVED / 'Build/Products'
        products.mkdir(parents=True)
        target = {
            'TestBundlePath': '__TESTHOST__/PlugIns/AppVerifyUITests.xctest',
            'EnvironmentVariables': {'DYLD_FRAMEWORK_PATH': '__TESTROOT__/Debug-iphonesimulator:/Developer/Library/Frameworks'},
            'TestingEnvironmentVariables': {'DYLD_LIBRARY_PATH': '__TESTROOT__/Debug-iphonesimulator'},
            'UITargetAppEnvironmentVariables': {'DYLD_FRAMEWORK_PATH': '__TESTROOT__/Debug-iphonesimulator'},
        }
        for plan in ({'TestConfigurations': [{'TestTargets': [target]}]}, {'AppVerifyUITests': target}):
            original = products / 'AppVerify_iphonesimulator.xctestrun'
            original.write_bytes(plistlib.dumps(plan))
            result = plistlib.loads(verify.isolated_xctestrun().read_bytes())
            isolated = (result['TestConfigurations'][0]['TestTargets'][0]
                        if 'TestConfigurations' in result else result['AppVerifyUITests'])
            self.assertEqual(isolated['TestBundlePath'], target['TestBundlePath'])
            self.assertEqual(isolated['EnvironmentVariables']['DYLD_FRAMEWORK_PATH'], '/Developer/Library/Frameworks')
            self.assertEqual(isolated['TestingEnvironmentVariables'], {})
            self.assertEqual(isolated['UITargetAppEnvironmentVariables'], {})
            self.assertEqual(plistlib.loads(original.read_bytes()), plan)


if __name__ == '__main__':
    unittest.main()
