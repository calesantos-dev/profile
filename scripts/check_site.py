#!/usr/bin/env python3
"""Check navigation, localized metadata, and contact details on all live pages."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import re
import json
import xml.etree.ElementTree as ET

from build_languages import ROOT, ORIGIN, LOCALES, PAGES, page_path


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids, self.links, self.alternates = set(), [], {}
        self.canonicals, self.lang, self.og_url, self.og_locale = [], None, None, None
        self.switches = 0
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            assert a["id"] not in self.ids, f"Duplicate ID: {a['id']}"
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        if a.get("class") == "language-switch":
            self.switches += 1
        if tag == "link" and a.get("rel") == "canonical":
            self.canonicals.append(a["href"])
        if tag == "link" and a.get("rel") == "alternate":
            assert a["hreflang"] not in self.alternates
            self.alternates[a["hreflang"]] = a["href"]
        if tag == "meta" and a.get("property") == "og:url":
            self.og_url = a["content"]
        if tag == "meta" and a.get("property") == "og:locale":
            self.og_locale = a["content"]
        for attr in ("href", "src"):
            if a.get(attr):
                self.links.append(a[attr])


def main():
    pages = {}
    clients = json.loads((ROOT / "images/clients/sources.json").read_text())["organizations"]
    for language, locale in LOCALES.items():
        for source in PAGES:
            path = source if language == "pt" else Path(language) / source
            text = (ROOT / path).read_text()
            page = Page(text)
            pages[path] = page
            expected = ORIGIN + page_path(source, language)
            assert page.lang == locale, path
            assert page.canonicals == [expected], path
            assert page.og_url == expected and page.og_locale == locale.replace("-", "_"), path
            assert page.switches == 1, path
            alternates = {value: ORIGIN + page_path(source, code) for code, value in LOCALES.items()}
            alternates["x-default"] = ORIGIN + page_path(source, "pt")
            assert page.alternates == alternates, path
            assert "mailto:" not in text and "profile-seven-wheat.vercel.app" not in text, path
            if str(source) == "index.html":
                assert len(re.findall(r'class="client-(?:name|text)"', text)) == len(clients), path
                assert 'id="clientes"' in text and 'aria-controls="client-marquee"' in text, path
                for client in clients:
                    assert client["name"] in text, (path, client["name"])
                    if client.get("logo"):
                        assert (ROOT / "images/clients" / client["logo"]).is_file(), client["name"]
                assert "2013" not in text, f"Outdated teaching dates: {path}"
            for target in page.links:
                if "wa.me/" in target:
                    assert target == "https://wa.me/244940203170", (path, target)
                if target.startswith("tel:"):
                    assert re.sub(r"\D", "", target) == "244940203170", (path, target)
    for path, page in pages.items():
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = ROOT / url.path.lstrip("/") if url.path.startswith("/") else ROOT / path.parent / url.path
            if not url.path:
                target = ROOT / path
            if target.is_dir():
                target = target / "index.html"
            assert target.is_file(), f"Broken local resource: {path} -> {link}"
            if url.fragment:
                destination = pages.get(target.relative_to(ROOT))
                assert destination and unquote(url.fragment) in destination.ids, f"Broken anchor: {path} -> {link}"
    sitemap = ET.parse(ROOT / "sitemap.xml")
    urls = {e.text for e in sitemap.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")}
    assert urls == {p.canonicals[0] for p in pages.values()}
    print(f"Checked {len(pages)} pages: language metadata, links, anchors, sitemap, and contact details are valid.")


if __name__ == "__main__":
    main()
