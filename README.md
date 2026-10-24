# Calembe dos Santos — portfolio

Static website at https://calembe.com, deployed on Vercel from the `main` branch.

## Languages

Portuguese (Angola) is maintained in `index.html` and `boletins/*.html`.
Reviewed translations live in `translations/en.json`, `fr.json`, and `es.json`.
They use the Portuguese text as keys; product names and certification titles
retain their official spelling.

After changing Portuguese content, update the matching keys in all three JSON
files, then run:

```sh
python3 scripts/build_languages.py
python3 scripts/check_site.py
```

The build produces `/en/` (US English), `/fr/` (France), and `/es/` (Spain),
including all articles, canonical links, language alternatives, and the sitemap.
Missing translations stop the build before any page is written. Generated
language controls also work without JavaScript. Do not edit the generated
language folders directly; commit the generated pages with their source changes.

For a local preview, run `python3 -m http.server 8765` from this directory.
