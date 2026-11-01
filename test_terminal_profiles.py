import plistlib
import unittest

from lib.terminal_profiles import make_opaque, opaque_color


def archive(color):
    return plistlib.dumps({
        '$archiver': 'NSKeyedArchiver',
        '$objects': ['$null', {**color, '$class': plistlib.UID(2)}, {'$classname': 'NSColor'}],
    }, fmt=plistlib.FMT_BINARY)


def color_of(data):
    return plistlib.loads(data)['$objects'][1]


class TestOpaqueColor(unittest.TestCase):
    def test_removes_alpha_from_rgb(self):
        data = opaque_color(archive({'NSRGB': b'0.1 0.2 0.3 0.95\x00', 'NSColorSpace': 1}))
        self.assertEqual(color_of(data)['NSRGB'], b'0.1 0.2 0.3\x00')

    def test_removes_alpha_from_white(self):
        data = opaque_color(archive({'NSWhite': b'0 0.85000002\x00', 'NSColorSpace': 3}))
        self.assertEqual(color_of(data)['NSWhite'], b'0\x00')

    def test_sets_alpha_to_one_in_components(self):
        data = opaque_color(archive({'NSComponents': b'1 1 1 0.93', 'NSRGB': b'1 1 1 0.93\x00'}))
        self.assertEqual(color_of(data)['NSComponents'], b'1 1 1 1')
        self.assertEqual(color_of(data)['NSRGB'], b'1 1 1\x00')

    def test_keeps_class_reference(self):
        data = opaque_color(archive({'NSRGB': b'0.1 0.2 0.3 0.95\x00'}))
        self.assertEqual(color_of(data)['$class'], plistlib.UID(2))

    def test_returns_opaque_color_unchanged(self):
        data = archive({'NSRGB': b'0.1 0.2 0.3\x00'})
        self.assertEqual(opaque_color(data), data)


class TestMakeOpaque(unittest.TestCase):
    def test_changes_translucent_profile(self):
        prefs = {'Window Settings': {'Pro': {'BackgroundColor': archive({'NSWhite': b'0 0.85\x00'})}}}
        self.assertEqual(make_opaque(prefs, ['Pro'], lambda name: None), ['Pro'])
        self.assertEqual(color_of(prefs['Window Settings']['Pro']['BackgroundColor'])['NSWhite'], b'0\x00')

    def test_second_run_changes_nothing(self):
        prefs = {'Window Settings': {'Pro': {'BackgroundColor': archive({'NSWhite': b'0 0.85\x00'})}}}
        make_opaque(prefs, ['Pro'], lambda name: None)
        self.assertEqual(make_opaque(prefs, ['Pro'], lambda name: None), [])

    def test_uses_builtin_color_when_profile_has_none(self):
        prefs = {'Window Settings': {'Clear Dark': {'shellExitAction': 1}}}
        builtin = lambda name: archive({'NSRGB': b'0.1 0.2 0.3 0.95\x00'})
        self.assertEqual(make_opaque(prefs, ['Clear Dark'], builtin), ['Clear Dark'])
        color = color_of(prefs['Window Settings']['Clear Dark']['BackgroundColor'])
        self.assertEqual(color['NSRGB'], b'0.1 0.2 0.3\x00')

    def test_skips_profile_without_any_color(self):
        prefs = {'Window Settings': {'Basic': {'shellExitAction': 1}}}
        self.assertEqual(make_opaque(prefs, ['Basic'], lambda name: None), [])
        self.assertNotIn('BackgroundColor', prefs['Window Settings']['Basic'])


if __name__ == '__main__':
    unittest.main()
