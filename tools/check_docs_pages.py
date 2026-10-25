"""Check built documentation links and assets without network access."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit


class LocalReferences(HTMLParser):
    """Collect browser references, not escaped examples inside code blocks."""

    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        for attr, value in attrs:
            if attr in ("href", "src") and value:
                self.references.append(value)


def check_build(dist, base):
    """Return page/reference counts and every invalid local reference."""
    dist = dist.resolve()
    pages = sorted(dist.rglob("*.html"))
    errors = []
    checked = 0
    if not pages:
        errors.append("No generated HTML pages found in %s" % dist)
    for page in pages:
        relative_page = page.relative_to(dist).as_posix()
        parser = LocalReferences()
        parser.feed(page.read_text(encoding="utf-8"))
        for value in parser.references:
            parsed = urlsplit(value)
            # External URLs and same-page fragments do not address build files.
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            checked += 1
            path = unquote(urlsplit(urljoin(base + relative_page, value)).path)
            if not path.startswith(base):
                errors.append("%s: %s is outside project base %s" % (relative_page, value, base))
                continue
            target = dist / path[len(base) :]
            if path.endswith("/"):
                target /= "index.html"
            elif not target.exists() and not target.suffix:
                target = target.with_suffix(".html")
            try:
                target.resolve().relative_to(dist)
            except ValueError:
                errors.append("%s: %s escapes the build directory" % (relative_page, value))
                continue
            if not target.is_file():
                errors.append("%s: %s has no built file" % (relative_page, value))
    if pages and not checked:
        errors.append("No local asset or navigation references were checked")
    return len(pages), checked, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path(__file__).resolve().parents[1] / "docs/.vitepress/dist")
    parser.add_argument("--base", default="/dcc-mcp-maya/")
    args = parser.parse_args()
    if not args.base.startswith("/") or not args.base.endswith("/") or args.base.startswith("//"):
        parser.error("--base must be an absolute project path ending in '/'")
    pages, checked, errors = check_build(args.dist, args.base)
    print("Docs build links: %d pages, %d local references, %d errors" % (pages, checked, len(errors)))
    for error in errors[:25]:
        print("ERROR: " + error)
    if len(errors) > 25:
        print("... %d additional errors" % (len(errors) - 25))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
