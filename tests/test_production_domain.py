"""Production source URLs must not depend on build-time domain replacement."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProductionDomainTest(unittest.TestCase):
    def test_public_sources_use_real_domain(self):
        sources = [ROOT / name for name in ('index.html', '404.html', 'sitemap.xml', 'robots.txt')]
        for directory in ('directions', 'services', 'team', 'cases', 'insights', 'contacts',
                          'privacy', 'cookies', 'personal-data-consent', 'en'):
            sources.extend(sorted((ROOT / directory).rglob('index.html')))
        self.assertEqual(len(sources), 45)
        for source in sources:
            with self.subTest(path=str(source.relative_to(ROOT))):
                self.assertNotIn('YOUR-DOMAIN.TLD', source.read_text())
                self.assertIn('https://axionica.ru', source.read_text())
