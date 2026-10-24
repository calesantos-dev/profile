#!/usr/bin/env python3
"""Build the static language pages from Portuguese HTML and reviewed JSON copy."""
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import json
import posixpath
import re

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://calembe.com"
LOCALES = {"pt": "pt-AO", "en": "en-US", "fr": "fr-FR", "es": "es-ES"}
NAMES = {"pt": "Português", "en": "English", "fr": "Français", "es": "Español"}
LABELS = {"pt": "Escolher idioma", "en": "Choose language", "fr": "Choisir la langue", "es": "Elegir idioma"}
# Resolve the article list independently of the caller's working directory.
PAGES = [Path("index.html"), *(p.relative_to(ROOT) for p in sorted((ROOT / "boletins").glob("*.html")))]
PAGE_NAMES = {p.as_posix() for p in PAGES}


def page_path(page, language):
    prefix = "" if language == "pt" else language + "/"
    return "/" + prefix + ("" if str(page) == "index.html" else str(page))


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def strip_generated(source):
    return re.sub(r"\n?[ \t]*<!-- i18n:(head|languages) -->.*?<!-- /i18n:\1 -->", "", source, flags=re.S)


class Localize(HTMLParser):
    def __init__(self, page, language, dictionary):
        super().__init__(convert_charrefs=True)
        self.page, self.language, self.dictionary = page, language, dictionary
        self.output = []
        self.skip = 0

    def translate(self, text):
        key = normalize(text)
        if self.language == "pt" or not re.search(r"[A-Za-zÀ-ÿ]", key):
            return text
        if key not in self.dictionary:
            raise ValueError(f"Missing {self.language} translation in {self.page}: {key}")
        leading = re.match(r"\s*", text).group()
        trailing = re.search(r"\s*$", text).group()
        return leading + self.dictionary[key] + trailing

    def local_url(self, value):
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc or not parsed.path:
            return value
        if parsed.path.startswith("/"):
            path = parsed.path.lstrip("/") or "index.html"
        else:
            path = posixpath.normpath(str(self.page.parent / parsed.path))
        path = path.rstrip("/")
        if path in PAGE_NAMES:
            path = page_path(path, self.language)
        else:
            path = "/" + path
        return urlunsplit(("", "", path, parsed.query, parsed.fragment))

    def start(self, tag, attrs, closed=False):
        values = dict(attrs)
        if tag in ("script", "style") and not closed:
            self.skip += 1
        updated = []
        for name, value in attrs:
            if value is None:
                updated.append(name)
                continue
            if name in ("alt", "aria-label", "title"):
                value = self.translate(value)
            elif tag == "html" and name == "lang":
                value = LOCALES[self.language]
            elif tag == "link" and values.get("rel") == "canonical" and name == "href":
                value = ORIGIN + page_path(self.page, self.language)
            elif tag == "meta" and name == "content":
                if values.get("property") == "og:url":
                    value = ORIGIN + page_path(self.page, self.language)
                elif values.get("property") == "og:locale":
                    value = LOCALES[self.language].replace("-", "_")
                elif values.get("name") == "description" or values.get("property") in ("og:title", "og:description"):
                    value = self.translate(value)
            elif name in ("href", "src"):
                value = self.local_url(value)
            updated.append(f'{name}="{escape(value, quote=True)}"')
        suffix = " /" if closed else ""
        self.output.append("<" + tag + (" " + " ".join(updated) if updated else "") + suffix + ">")

    def handle_starttag(self, tag, attrs):
        self.start(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        self.start(tag, attrs, True)

    def handle_endtag(self, tag):
        self.output.append(f"</{tag}>")
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, data):
        self.output.append(data if self.skip else escape(self.translate(data), quote=False))

    def handle_decl(self, decl):
        self.output.append(f"<!{decl}>")

    def handle_comment(self, data):
        self.output.append(f"<!--{data}-->")


def finish(html, page, language):
    alternates = [f'<link rel="alternate" hreflang="{locale}" href="{ORIGIN}{page_path(page, code)}" />' for code, locale in LOCALES.items()]
    alternates.append(f'<link rel="alternate" hreflang="x-default" href="{ORIGIN}{page_path(page, "pt")}" />')
    head = "\n    <!-- i18n:head -->\n    " + "\n    ".join(alternates) + "\n    <!-- /i18n:head -->"
    html = html.replace("\n  </head>", head + "\n  </head>", 1)
    links = []
    for code, locale in LOCALES.items():
        current = ' aria-current="true"' if code == language else ""
        links.append(f'<a href="{page_path(page, code)}" lang="{locale}" hreflang="{locale}"{current}>{NAMES[code]}<span aria-hidden="true">{code.upper()}</span></a>')
    selector = f'''\n        <!-- i18n:languages -->
        <details class="language-switch">
          <summary aria-label="{LABELS[language]}">{language.upper()} <span aria-hidden="true">⌄</span></summary>
          <div class="language-options">{"".join(links)}</div>
        </details>
        <!-- /i18n:languages -->'''
    return html.replace("</nav>", "</nav>" + selector, 1)


def main():
    sources = {page: strip_generated((ROOT / page).read_text()) for page in PAGES}
    dictionaries = {language: json.loads((ROOT / "translations" / f"{language}.json").read_text()) for language in LOCALES if language != "pt"}
    # Render everything before writing: missing copy must never leave a partial build.
    rendered = {}
    for language in LOCALES:
        for page, source in sources.items():
            parser = Localize(page, language, dictionaries.get(language, {}))
            parser.feed(source)
            parser.close()
            target = page if language == "pt" else Path(language) / page
            rendered[target] = finish("".join(parser.output), page, language)
    for target, html in rendered.items():
        (ROOT / target).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / target).write_text(html)
    urls = [ORIGIN + page_path(page, language) for language in LOCALES for page in PAGES]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "".join(f"  <url><loc>{url}</loc></url>\n" for url in urls) + "</urlset>\n"
    (ROOT / "sitemap.xml").write_text(sitemap)
    print(f"Built {len(rendered)} pages in {len(LOCALES)} languages; translation coverage complete.")


if __name__ == "__main__":
    main()
