"""Real nginx integration checks. Requires Docker and Python 3 stdlib only."""
import gzip
import hashlib
import json
import subprocess

import time
import unittest
import importlib.util
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_site', ROOT / 'scripts/build_site.py')
assert spec is not None and spec.loader is not None
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        self.urls.extend(value for key, value in attrs if key in ('href', 'src') and value)


class NginxSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert (ROOT / "deploy/nginx.conf").is_file(), "nginx configuration is missing"
        assert (ROOT / "scripts/build_site.py").is_file(), "publication builder is missing"
        subprocess.run(["python3", str(ROOT / "scripts/build_site.py")], check=True)
        cls.assets = json.loads((ROOT / 'dist/.axionica-build').read_text())["assets"]
        subprocess.run([
            'docker', 'run', '--rm',
            '-v', str(ROOT / 'deploy/nginx.conf') + ':/etc/nginx/conf.d/default.conf:ro',
            'nginx:stable-alpine', 'nginx', '-t',
        ], check=True)
        cls.container = subprocess.check_output([
            "docker", "run", "--rm", "-d", "-p", "127.0.0.1::80",
            "-v", str(ROOT / "dist") + ":/var/www/axionica/current:ro",
            "-v", str(ROOT / "deploy/nginx.conf") + ":/etc/nginx/conf.d/default.conf:ro",
            "nginx:stable-alpine",
        ], text=True).strip()
        cls.addClassCleanup(subprocess.run, ["docker", "stop", cls.container],
                            check=True, stdout=subprocess.DEVNULL)
        port = subprocess.check_output(["docker", "port", cls.container, "80/tcp"], text=True)
        cls.base = "http://" + port.strip()
        for attempt in range(50):
            try:
                with urlopen(cls.base + "/ru/", timeout=2):
                    break
            except (URLError, ConnectionError):
                if attempt == 49:
                    raise
                time.sleep(0.1)
        subprocess.run(["docker", "exec", cls.container, "nginx", "-t"], check=True)

    def fetch(self, path, method="GET", headers=None):
        try:
            return urlopen(Request(self.base + path, method=method, headers=headers or {}), timeout=5)
        except HTTPError as response:
            return response

    def test_pages_and_resources_match_published_bytes(self):
        for file in sorted((ROOT / "dist").rglob("*")):
            if not file.is_file():
                continue
            path = "/" + file.relative_to(ROOT / "dist").as_posix()
            if path in ("/index.html", "/.axionica-build"):
                continue
            path = builder.page_url(path)
            with self.subTest(path=path), self.fetch(path) as response:
                self.assertEqual(response.status, 404 if path == "/404.html" else 200)
                self.assertEqual(response.read(), file.read_bytes())

    def test_all_page_links_metadata_and_assets_resolve(self):
        seen = set()
        for file in sorted((ROOT / 'dist').glob('*/**/index.html')):
            page = builder.page_url('/' + file.relative_to(ROOT / 'dist').as_posix())
            parser = References()
            parser.feed(file.read_text())
            for value in parser.urls:
                target = urlsplit(urljoin('https://axionica.ru' + page, value))
                if target.netloc != 'axionica.ru':
                    continue
                self.assertFalse(target.path.endswith('.html'), (page, value))
                if target.path not in seen:
                    seen.add(target.path)
                    with self.subTest(page=page, target=target.path), self.fetch(target.path) as response:
                        self.assertEqual(response.status, 200)

    def test_clean_pages_head_mime_queries_and_old_urls(self):
        for file in sorted((ROOT / 'dist').glob('*/**/index.html')):
            source = '/' + file.relative_to(ROOT / 'dist').as_posix()
            clean = builder.page_url(source)
            with self.subTest(clean=clean), self.fetch(clean + '?source=test') as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.geturl(), self.base + clean + '?source=test')
                self.assertEqual(response.read(), file.read_bytes())
            with self.fetch(clean, method='HEAD') as response:
                self.assertEqual(response.status, 200)
                self.assertIn('text/html', response.headers['Content-Type'])
                self.assertEqual(response.read(), b'')
            parts = clean.strip('/').split('/')
            old = '/' + parts[0] + '/' + (parts[-1] if len(parts) > 1 else 'index') + '.html'
            for alias in set((old, source, clean.rstrip('/') + '.html')):
                with self.subTest(alias=alias), self.fetch(alias) as response:
                    self.assertEqual(response.status, 404)
                    self.assertEqual(response.geturl(), self.base + alias)
            with self.fetch(clean.rstrip('/') + '?source=slash') as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.geturl(), self.base + clean + '?source=slash')
                self.assertEqual(response.read(), file.read_bytes())

    def test_sitemap_matches_canonical_and_language_versions(self):
        namespace = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                     'x': 'http://www.w3.org/1999/xhtml'}
        tree = ElementTree.parse(ROOT / 'dist/sitemap.xml')
        locations = [entry.text for entry in tree.findall('s:url/s:loc', namespace)]
        pages = sorted((ROOT / 'dist').glob('*/**/index.html'))
        expected = {'https://axionica.ru' + builder.page_url('/' + page.relative_to(ROOT / 'dist').as_posix())
                    for page in pages}
        self.assertEqual(len(locations), len(expected))
        self.assertEqual(set(locations), expected)
        for page in pages:
            source = '/' + page.relative_to(ROOT / 'dist').as_posix()
            canonical = 'https://axionica.ru' + builder.page_url(source)
            self.assertIn('rel="canonical" href="' + canonical + '"', page.read_text())
            for language in ('ru', 'en'):
                alternate = 'https://axionica.ru' + builder.page_url('/' + language + '/' + page.relative_to(ROOT / 'dist').as_posix().split('/', 1)[1])
                self.assertIn('hreflang="' + language + '" href="' + alternate + '"', page.read_text())
        for alternate in tree.findall('s:url/x:link', namespace):
            self.assertIn(alternate.attrib['href'], expected)

    def test_language_indexes_and_root_redirect(self):
        for path, target in [("/", "/ru/"), ("/index.html", "/ru/"),
                             ("/ru", "/ru/"), ("/en", "/en/")]:
            with self.subTest(path=path), self.fetch(path + "?source=test") as response:
                self.assertEqual(response.geturl(), self.base + target + "?source=test")
                self.assertEqual(response.read(), (ROOT / "dist" / target.strip("/") / "index.html").read_bytes())
        for language in ("ru", "en"):
            with self.fetch("/" + language + "/") as response:
                self.assertEqual(response.read(), (ROOT / 'dist' / language / "index.html").read_bytes())

    def asset_url(self, source):
        return '/' + self.assets[source]

    def test_hashed_assets_are_immutable_and_match_their_hashes(self):
        for source, target in self.assets.items():
            with self.subTest(source=source), self.fetch('/' + target + '?cache=test') as response:
                self.assertEqual(response.status, 200)
                content = response.read()
                self.assertEqual(content, (ROOT / 'dist' / target).read_bytes())
                self.assertEqual(Path(target).stem.rsplit('.', 1)[1], hashlib.sha256(content).hexdigest()[:16])
                self.assertEqual(response.headers['Cache-Control'], 'public, max-age=31536000, immutable')
            with self.fetch('/' + source) as response:
                self.assertEqual(response.status, 404)

    def test_head_mime_cache_and_security(self):
        for path, mime in [("/ru/", "text/html"), ("/assets/css/main.css", "text/css"),
                           ("/assets/js/main.js", "application/javascript"),
                           ("/assets/icons/logo.svg", "image/svg+xml"),
                           ("/manifest.webmanifest", "application/manifest+json"),
                           ("/sitemap.xml", "text/xml"), ("/robots.txt", "text/plain")]:
            if path.startswith('/assets/'):
                path = self.asset_url(path.lstrip('/'))
            with self.subTest(path=path), self.fetch(path, method="HEAD") as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read(), b"")
                self.assertIn(mime, response.headers["Content-Type"])
                self.assertIsNotNone(response.headers["ETag"])
                self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
                self.assertEqual(response.headers["X-Frame-Options"], "SAMEORIGIN")
                self.assertIn("max-age=31536000, immutable" if path.startswith("/assets/") else "no-cache",
                              response.headers["Cache-Control"])

    def test_gzip_and_conditional_request(self):
        with self.fetch(self.asset_url('assets/css/main.css'), headers={"Accept-Encoding": "gzip"}) as response:
            self.assertEqual(response.headers["Content-Encoding"], "gzip")
            self.assertEqual(gzip.decompress(response.read()), (ROOT / 'dist' / self.assets['assets/css/main.css']).read_bytes())
        with self.fetch("/ru/") as response:
            etag = response.headers["ETag"]
        with self.fetch("/ru/", headers={"If-None-Match": etag}) as response:
            self.assertEqual(response.status, 304)

    def test_missing_and_private_paths_return_authored_404(self):
        for path in ("/missing", "/ru/missing.html", "/en/missing.html", "/ru/team.html/",
                     "/assets/missing.css", "/assets/css/main.css.bak", "/.git/config",
                     "/README.md", "/Prompt.md", "/deploy/nginx.conf", "/scripts/build_site.py",
                     "/assets/", "/assets/css/", "/ru/.hidden", "/.axionica-build", "/ru/../README.md"):
            with self.subTest(path=path), self.fetch(path) as response:
                self.assertEqual(response.status, 404)
                self.assertEqual(response.read(), (ROOT / "dist/404.html").read_bytes())

    def test_publication_contains_only_public_files(self):
        files = {p.relative_to(ROOT / "dist").as_posix() for p in (ROOT / "dist").rglob("*") if p.is_file()}
        self.assertIn("ru/index.html", files)
        self.assertIn("en/index.html", files)
        self.assertNotIn("assets/css/main.css.bak", files)
        self.assertFalse(any(p.startswith(("deploy/", "scripts/", "tests/", ".git/")) or p.endswith(".md") for p in files))


if __name__ == "__main__":
    unittest.main(verbosity=2)
