from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from spire.steam import discover, layout, library_paths, pairs
from spire.setup import install, FILES


def fake_game(root, system='Darwin'):
    if system == 'Darwin':
        executable = root / 'SlayTheSpire2.app/Contents/MacOS/Slay the Spire 2'
        data = root / 'SlayTheSpire2.app/Contents/Resources/data_sts2_macos_arm64'
    else:
        executable = root / ('SlayTheSpire2.exe' if system == 'Windows' else 'SlayTheSpire2')
        data = root / ('data_sts2_windows_x86_64' if system == 'Windows' else 'data_sts2_linuxbsd_x86_64')
    executable.parent.mkdir(parents=True, exist_ok=True); executable.write_text('test executable')
    data.mkdir(parents=True, exist_ok=True)
    for name in ('sts2.dll', 'GodotSharp.dll', '0Harmony.dll'): (data / name).write_text('test reference')
    return layout(root, system, 'arm64')


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_layout_all_platforms(self):
        for system in ('Windows', 'Darwin', 'Linux'):
            game = fake_game(self.root / system, system)
            self.assertTrue(game['data_dir'].is_dir())
            self.assertEqual(game['mods_dir'], game['executable'].parent / 'mods')

    def test_vdf_windows_and_unicode(self):
        parsed = dict(pairs('"path" "D:\\\\SteamLibrary" "name" "游戏库"'))
        self.assertEqual(parsed['path'], 'D:\\SteamLibrary')
        self.assertEqual(parsed['name'], '游戏库')

    def test_discovers_secondary_library(self):
        steam = self.root / 'Steam'; extra = self.root / 'Other Drive'
        (steam / 'steamapps').mkdir(parents=True)
        (steam / 'steamapps/libraryfolders.vdf').write_text('"1" { "path" "' + extra.as_posix() + '" }')
        game = fake_game(extra / 'steamapps/common/Slay the Spire 2')
        (extra / 'steamapps/appmanifest_2868840.acf').write_text('"AppState" { "installdir" "Slay the Spire 2" }')
        with patch('spire.steam.platform.system', return_value='Darwin'), patch('spire.steam.platform.machine', return_value='arm64'), patch.dict('os.environ', {}, clear=True):
            self.assertEqual(discover(roots=[steam]), game)

    def test_missing_installation_is_explicit(self):
        with patch.dict('os.environ', {}, clear=True), self.assertRaises(ValueError):
            discover(roots=[self.root])

    def build_output(self):
        output = self.root / 'build'; output.mkdir()
        for name in FILES: (output / name).write_text('our mod')
        return output

    def test_install_update_uninstall_preserves_other_files(self):
        game = fake_game(self.root / 'game'); output = self.build_output()
        receipt = self.root / 'receipt.json'
        game['mods_dir'].mkdir(); other = game['mods_dir'] / 'AnotherMod.dll'; other.write_text('unrelated')
        install(game, output, receipt)
        (output / FILES[0]).write_text('updated mod')
        install(game, output, receipt)
        self.assertEqual((game['mods_dir'] / FILES[0]).read_text(), 'updated mod')
        install(game, None, receipt, uninstall=True)
        self.assertEqual(other.read_text(), 'unrelated')
        self.assertFalse(receipt.exists())

    def test_refuses_unowned_files_before_any_write(self):
        game = fake_game(self.root / 'game'); output = self.build_output()
        game['mods_dir'].mkdir(); collision = game['mods_dir'] / FILES[1]; collision.write_text('someone else')
        with self.assertRaises(ValueError): install(game, output, self.root / 'receipt.json')
        self.assertFalse((game['mods_dir'] / FILES[0]).exists())
        self.assertEqual(collision.read_text(), 'someone else')

    def test_receipt_failure_rolls_back_install(self):
        game = fake_game(self.root / 'game'); output = self.build_output()
        with patch.object(Path, 'write_text', side_effect=OSError('disk full')):
            with self.assertRaises(OSError): install(game, output, self.root / 'receipt.json')
        self.assertFalse(any((game['mods_dir'] / name).exists() for name in FILES))
