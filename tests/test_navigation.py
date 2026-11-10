"""Run active-navigation logic without opening a browser."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'Node.js required for navigation behavior')
class NavigationTest(unittest.TestCase):
    def test_only_matching_directory_link_is_active(self):
        source = (ROOT / 'assets/js/main.js').read_text().split('/* ---------- Mobile menu')[0]
        for current, expected in [('/ru/', '/ru/'),
                                  ('/ru/directions/', '/ru/directions/'),
                                  ('/ru/directions/studio/', '/ru/directions/studio/'),
                                  ('/en/services/discovery/', '/en/services/discovery/')]:
            links = ['/ru/', '/ru/directions/', '/ru/directions/studio/', '/en/services/discovery/']
            setup = '''const links = LINKS.map(href => ({href, active:false,
classList:{toggle(name,on){this.owner.active=on}},
getAttribute(){return this.href},setAttribute(){},removeAttribute(){},closest(){return null}}));
links.forEach(link => link.classList.owner=link);
const menu={querySelectorAll(){return links}};
const document={querySelector(selector){return selector==='[data-nav]'?menu:null},querySelectorAll(){return []}};
const window={location:{pathname:CURRENT,href:'https://axionica.ru'+CURRENT},matchMedia(){return {matches:false}}};
'''.replace('LINKS', json.dumps(links)).replace('CURRENT', json.dumps(current))
            result = subprocess.run(['node', '-e', setup + source + '\nconsole.log(JSON.stringify(links.filter(l=>l.active).map(l=>l.href)))'],
                                    check=True, capture_output=True, text=True)
            self.assertEqual(json.loads(result.stdout), [expected])
