import os
import plistlib
import sys

PREFERENCES = os.path.expanduser('~/Library/Preferences/com.apple.Terminal.plist')
BUILTIN_PROFILES = '/System/Applications/Utilities/Terminal.app/Contents/Resources/Initial Settings'
CHANNELS = {'NSRGB': 3, 'NSWhite': 1}


def opaque_value(key, value):
    terminator = b'\0' if value.endswith(b'\0') else b''
    parts = value.rstrip(b'\0').split()
    if key == 'NSComponents':
        parts[-1] = b'1'
    else:
        parts = parts[:CHANNELS[key]]
    return b' '.join(parts) + terminator


def opaque_color(data):
    archive = plistlib.loads(data)
    changed = False
    for item in archive['$objects']:
        if not isinstance(item, dict):
            continue
        for key in ('NSRGB', 'NSWhite', 'NSComponents'):
            if key in item:
                desired = opaque_value(key, item[key])
                changed = changed or desired != item[key]
                item[key] = desired
    return plistlib.dumps(archive, fmt=plistlib.FMT_BINARY) if changed else data


def builtin_color(name):
    try:
        with open(os.path.join(BUILTIN_PROFILES, f'{name}.terminal'), 'rb') as f:
            return plistlib.load(f).get('BackgroundColor')
    except FileNotFoundError:
        return None


def make_opaque(prefs, names, builtin=builtin_color):
    changed = []
    profiles = prefs.setdefault('Window Settings', {})
    for name in names:
        profile = profiles.setdefault(name, {})
        current = profile.get('BackgroundColor') or builtin(name)
        if current is None:
            continue
        desired = opaque_color(current)
        if desired != profile.get('BackgroundColor'):
            profile['BackgroundColor'] = desired
            changed.append(name)
    return changed


def main():
    with open(PREFERENCES, 'rb') as f:
        prefs = plistlib.load(f)
    changed = make_opaque(prefs, sys.argv[1:])
    if changed:
        with open(PREFERENCES, 'wb') as f:
            plistlib.dump(prefs, f, fmt=plistlib.FMT_BINARY)
    print('RESULT=CHANGED' if changed else 'RESULT=UNCHANGED')


if __name__ == '__main__':
    main()
