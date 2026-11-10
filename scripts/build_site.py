#!/usr/bin/env python3
"""Build a whitelisted static publication with dependency-first SHA256 assets."""
import hashlib
import json
import posixpath
import re
import shutil
from urllib.parse import urlsplit

TEXT_EXTENSIONS = {".html", ".css", ".js", ".svg", ".webmanifest", ".xml", ".txt"}
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist"
MARKER = ".axionica-build"
PUBLIC_ROOT = ("index.html", "404.html", "robots.txt", "sitemap.xml", "manifest.webmanifest")
ASSET_EXTENSIONS = {".css", ".js", ".svg", ".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif", ".ico", ".woff", ".woff2"}

def page_url(path):
    """Directory indexes have the same public path as their owning folder."""
    return path[:-len('index.html')] if path.endswith('/index.html') else path


def rewrite_text(text, owner, resolve):
    """Rewrite literal asset URLs, not arbitrary substrings or dynamic JS.

    Current sources use quoted HTML/SVG/manifest/JS URLs, CSS url() and
    @import. Comments and complete data/external URLs stay opaque.
    """
    def url(value):
        parsed = urlsplit(value)
        if not parsed.path or value.startswith('#'):
            return value
        if parsed.scheme or parsed.netloc:
            return value
        path = posixpath.normpath(parsed.path.lstrip('/') if value.startswith('/') else
                                  posixpath.join(posixpath.dirname(owner), parsed.path))

        if not path.startswith('assets/') or (Path(parsed.path).suffix.lower() not in ASSET_EXTENSIONS | {'.bak', '.md'}
                                               and 'assets/' not in parsed.path):
            return value
        target = resolve(path)
        rewritten = '/' + target if value.startswith('/') or owner.endswith('.html') else posixpath.relpath(target, posixpath.dirname(owner) or '.')
        if value.startswith('./') and not rewritten.startswith(('.', '/')):
            rewritten = './' + rewritten
        return rewritten + value[len(parsed.path):]

    def token(match):
        item = match.group(0)
        if item.startswith(('/*', '<!--', '//')):
            return item
        if item[:1] in ('"', "'", '`'):
            value = item[1:-1]
            if value.startswith(('data:', 'http:', 'https:', '//')):
                return item
            if 'url(' in value:
                value = rewrite_text(value, owner, resolve)
            else:
                # srcset has whitespace-delimited URLs/descriptors.
                value = re.sub(r'[^\s,]+', lambda m: url(m.group(0)), value)
            return item[0] + value + item[-1]
        return re.sub(r'(?<=\()\s*([^\s)]+)\s*(?=\))', lambda m: url(m.group(1)), item)

    pattern = r'''/\*.*?\*/|<!--.*?-->|(?m:^\s*//[^\n]*)|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|url\(\s*[^'"\s][^)]*\)'''
    return re.sub(pattern, token, text.replace('YOUR-DOMAIN.TLD', 'axionica.ru'), flags=re.DOTALL)


def build():
    files = [ROOT / name for name in PUBLIC_ROOT]
    for language in ("ru", "en"):
        pages = sorted(path for path in (ROOT / language).rglob("index.html")
                       if not any(part.startswith('.') for part in path.relative_to(ROOT).parts))
        if not (ROOT / language / "index.html").is_file():
            raise SystemExit("Missing language homepage: " + language)
        files.extend(pages)
    files.extend(sorted(path for path in (ROOT / "assets").rglob("*")
                        if path.is_file() and path.suffix.lower() in ASSET_EXTENSIONS
                        and not any(part.startswith(".") for part in path.relative_to(ROOT).parts)))
    for source in files:
        if not source.is_file() or any(path.is_symlink() for path in (source, *source.parents)):
            raise SystemExit("Missing file or symlink in public input: " + str(source))
    data = {source.relative_to(ROOT).as_posix(): source.read_bytes() for source in files}
    mapping, generated = {}, {}
    visiting = []

    def render(name):
        content = data[name]
        if Path(name).suffix.lower() in TEXT_EXTENSIONS:
            return rewrite_text(content.decode('utf-8'), name, asset).encode('utf-8')
        return content

    def asset(name):
        if name not in mapping:
            if name in visiting:
                raise SystemExit('Asset dependency cycle: ' + ' -> '.join(visiting + [name]))
            if name not in data:
                raise SystemExit('Missing or non-public asset reference: ' + name)
            visiting.append(name)
            content = render(name)
            visiting.pop()
            path = Path(name)
            target = path.with_name(path.stem + '.' + hashlib.sha256(content).hexdigest()[:16] + path.suffix).as_posix()
            mapping[name] = target
            generated[target] = content
        return mapping[name]

    for name in sorted(data):
        if name.startswith('assets/'):
            asset(name)
        else:
            generated[name] = render(name)
    if OUTPUT.is_symlink():
        raise SystemExit("Refusing symlink output: " + str(OUTPUT))
    if OUTPUT.exists():
        if not (OUTPUT / MARKER).is_file() or (OUTPUT / MARKER).is_symlink():
            raise SystemExit("Refusing to replace unmanaged dist directory")
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir()
    for name, content in sorted(generated.items()):
        target = OUTPUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        target.chmod(0o644)
    (OUTPUT / MARKER).write_text(json.dumps({"assets": mapping}, sort_keys=True) + "\n", encoding="utf-8")
    print("Published {} files to {}".format(len(files), OUTPUT))


if __name__ == "__main__":
    build()
