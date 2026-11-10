"""Real nginx integration checks. Requires Docker and Python 3 stdlib only."""
import gzip
import hashlib
import json
import subprocess

import time
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


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
            with self.subTest(path=path), self.fetch(path) as response:
                self.assertEqual(response.status, 404 if path == "/404.html" else 200)
                self.assertEqual(response.read(), file.read_bytes())

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
