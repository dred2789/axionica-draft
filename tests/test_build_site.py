"""Dependency-free publication build contracts; no browser required."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_site", ROOT / "scripts/build_site.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuildSiteTest(unittest.TestCase):
    def setUp(self):
        scratch = Path.home() / '.hermes/cache/scratch'
        self.temp = tempfile.TemporaryDirectory(dir=scratch if scratch.is_dir() else None)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.output = self.root / "dist"
        for name in builder.PUBLIC_ROOT:
            self.put(name, "https://YOUR-DOMAIN.TLD/ru/" if name != "manifest.webmanifest" else '{}')
        for language in ("ru", "en"):
            self.put(language + "/index.html", '<img src="../assets/icons/logo.svg">')
        self.put("assets/icons/logo.svg", '<svg xmlns="http://www.w3.org/2000/svg"/>')
        for name, value in (("ROOT", self.root), ("OUTPUT", self.output)):
            context = patch.object(builder, name, value)
            context.start()
            self.addCleanup(context.stop)

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode())

    def mapping(self):
        return json.loads((self.output / builder.MARKER).read_text())["assets"]

    def test_directory_indexes_are_discovered_recursively(self):
        for language in ('ru', 'en'):
            self.put(language + '/directions/studio/index.html', '<a href="/' + language + '/">Home</a>')
        builder.build()
        for language in ('ru', 'en'):
            self.assertTrue((self.output / language / 'directions/studio/index.html').is_file())
            self.assertEqual(builder.page_url('/' + language + '/directions/studio/index.html'),
                             '/' + language + '/directions/studio/')

    def test_clean_nested_page_urls_and_resources(self):
        self.put('ru/services/discovery/index.html', '''<link rel="canonical" href="https://YOUR-DOMAIN.TLD/ru/services/discovery/">
<a href="/en/services/discovery/">EN</a><a href="/ru/directions/studio/?from=service#work">Studio</a>
<a href="/ru/services/">Services</a><a href="/ru/">Home</a>
<img src="/assets/icons/logo.svg"><a href="https://example.com/ru/studio.html">External</a>''')
        builder.build()
        html = (self.output / 'ru/services/discovery/index.html').read_text()
        for expected in ('https://axionica.ru/ru/services/discovery/', '/en/services/discovery/',
                         '/ru/directions/studio/?from=service#work', '/ru/services/', '/ru/',
                         '/' + self.mapping()['assets/icons/logo.svg'],
                         'https://example.com/ru/studio.html'):
            self.assertIn('"' + expected + '"', html)

    def test_private_asset_references_fail(self):
        self.put('assets/css/main.css.bak', 'private')
        self.put('assets/css/main.css', 'x{background:url(main.css.bak)}')
        with self.assertRaisesRegex(SystemExit, 'non-public.*main.css.bak'):
            builder.build()

    def test_missing_assets_fail_without_destroying_previous_build(self):
        builder.build()
        previous = (self.output / builder.MARKER).read_bytes()
        self.put('assets/css/main.css', 'x{background:url(../images/missing.jpg)}')
        with self.assertRaisesRegex(SystemExit, 'Missing.*assets/images/missing.jpg'):
            builder.build()
        self.assertEqual((self.output / builder.MARKER).read_bytes(), previous)

    def test_cycles_fail_clearly_without_destroying_previous_build(self):
        builder.build()
        self.put('assets/css/a.css', '@import "b.css";')
        self.put('assets/css/b.css', '@import "a.css";')
        with self.assertRaisesRegex(SystemExit, 'cycle.*a.css.*b.css.*a.css'):
            builder.build()
        self.assertTrue((self.output / 'ru/index.html').is_file())

    def test_private_files_and_symlinks_are_not_published(self):
        for name in ('secret.md', 'assets/.hidden.css', 'assets/css/main.css.bak', 'ru/.hidden.html', 'ru/private.md'):
            self.put(name, 'private')
        builder.build()
        files = [p.relative_to(self.output).as_posix() for p in self.output.rglob('*') if p.is_file()]
        self.assertFalse(any('hidden' in p or 'private' in p or p.endswith(('.md', '.bak')) for p in files))
        (self.root / 'assets/icons/linked.svg').symlink_to(self.root / 'assets/icons/logo.svg')
        with self.assertRaisesRegex(SystemExit, 'symlink'):
            builder.build()

    def test_unmanaged_and_symlink_outputs_are_refused(self):
        self.output.mkdir()
        self.put('dist/personal.txt', 'keep me')
        with self.assertRaisesRegex(SystemExit, 'unmanaged'):
            builder.build()
        self.assertEqual((self.output / 'personal.txt').read_text(), 'keep me')
        import shutil
        shutil.rmtree(self.output)
        self.output.symlink_to(self.root / 'ru', target_is_directory=True)
        with self.assertRaisesRegex(SystemExit, 'symlink output'):
            builder.build()

    def test_inline_css_and_opaque_external_data_comments(self):
        self.put('assets/css/main.css', '''/* url(../fonts/not-installed.woff2) */
x { background: url("https://example.com/assets/missing.svg"); mask:url(data:image/svg+xml,%3Csvg%3E); fill:url(#gradient) }''')
        self.put('ru/index.html', '''<div style="background:url('../assets/icons/logo.svg')"></div>
<!-- <img src="../assets/missing.svg"> -->
<img src="https://example.com/assets/no.svg"><a href="#thing">anchor</a>''')
        builder.build()
        html = (self.output / 'ru/index.html').read_text()
        self.assertIn("url('/" + self.mapping()['assets/icons/logo.svg'] + "')", html)
        self.assertIn('https://example.com/assets/no.svg', html)
        css = (self.output / self.mapping()['assets/css/main.css']).read_text()
        self.assertIn('url(data:image/svg+xml,%3Csvg%3E)', css)
        self.assertIn('url(#gradient)', css)
        self.assertIn('url(../fonts/not-installed.woff2)', css)

    def test_dependency_rewrites_cascade_and_builds_are_deterministic(self):
        self.put('assets/images/photo.jpg', b'image-one')
        self.put('assets/images/sprite.svg', '<svg><image href="photo.jpg"/><use href="#local"/></svg>')
        self.put('assets/css/base.css', 'a{background:url(../images/photo.jpg?v=2#crop)}')
        self.put('assets/css/main.css', '@import "base.css"; b{background:url("../images/sprite.svg#icon")}')
        self.put('assets/js/main.js', 'fetch("../images/sprite.svg"); const image="/assets/images/photo.jpg";')
        self.put('ru/index.html', '<link href="../assets/css/main.css"><script src="../assets/js/main.js"></script><img srcset="../assets/images/photo.jpg 1x, /assets/images/photo.jpg 2x"><style>x{background:url(../assets/images/photo.jpg)}</style>')
        self.put('manifest.webmanifest', '{"icons":[{"src":"/assets/images/photo.jpg"}]}')
        builder.build()
        first = self.mapping()
        for name, target in first.items():
            content = (self.output / target).read_bytes()
            self.assertEqual(Path(target).stem.rsplit('.', 1)[1], hashlib.sha256(content).hexdigest()[:16], name)
        css = (self.output / first['assets/css/base.css']).read_text()
        self.assertIn('../images/' + Path(first['assets/images/photo.jpg']).name + '?v=2#crop', css)
        main = (self.output / first['assets/css/main.css']).read_text()
        self.assertIn(Path(first['assets/css/base.css']).name, main)
        js = (self.output / first['assets/js/main.js']).read_text()
        self.assertIn('../images/' + Path(first['assets/images/sprite.svg']).name, js)
        self.assertIn('/' + first['assets/images/photo.jpg'], js)
        self.assertIn('/' + first['assets/images/photo.jpg'], (self.output / 'manifest.webmanifest').read_text())
        html = (self.output / 'ru/index.html').read_text()
        self.assertNotIn('photo.jpg', html)
        self.assertIn('#local', (self.output / first['assets/images/sprite.svg']).read_text())
        snapshot = {p.relative_to(self.output): p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        builder.build()
        self.assertEqual(snapshot, {p.relative_to(self.output): p.read_bytes() for p in self.output.rglob('*') if p.is_file()})
        self.put('assets/images/photo.jpg', b'image-two')
        builder.build()
        for name in first:
            if name != 'assets/icons/logo.svg':
                self.assertNotEqual(first[name], self.mapping()[name], name)
                self.assertFalse((self.output / first[name]).exists())

    def test_assets_have_content_hashes_and_sources_are_unchanged(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        builder.build()
        expected = "assets/icons/logo." + hashlib.sha256(before[Path('assets/icons/logo.svg')]).hexdigest()[:16] + ".svg"
        self.assertTrue((self.output / expected).is_file(), "asset filename must contain its SHA256 prefix")
        self.assertEqual(self.mapping(), {"assets/icons/logo.svg": expected})
        self.assertFalse((self.output / 'assets/icons/logo.svg').exists())
        self.assertIn('/' + expected, (self.output / 'ru/index.html').read_text())
        self.assertEqual((self.output / 'sitemap.xml').read_text(), 'https://axionica.ru/ru/')
        for name, data in before.items():
            self.assertEqual((self.root / name).read_bytes(), data)


if __name__ == '__main__':
    unittest.main(verbosity=2)
