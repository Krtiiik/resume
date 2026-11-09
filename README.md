# Resume

This is my resume, published at <https://krtiiik.github.io/resume/>.

The data lives in `resume.json` ([JSON Resume](https://www.jsonresume.org/) format), the layout and styling in `templates/` (`template.html`, with `style.css` inlined into it). The build renders them into a single self-contained `resumes/index.html` (the Source Serif 4 font is embedded from `templates/fonts/`), then prints it to a PDF named after the person (e.g. `resumes/lukas-nedbalek-resume.pdf`):

```
uv run build.py
```

The PDF is made by headless Chrome, Chromium or Edge, found on `PATH` or in the usual Windows install folders; set `RESUME_BROWSER` to a browser executable to override this. Without a browser the PDF is skipped with a warning and the page omits its PDF link.

## Phone number

The phone number is kept out of reach of scrapers. `basics.phone` in `resume.json` holds it encrypted, never as plain text, and the build draws the decrypted number as SVG glyph outlines in the contact row, so neither the page's HTML nor the PDF's text contains it (and there is no `tel:` link). To set or change it, pick a passphrase, then run the helper and paste the string it prints into `basics.phone`:

```
RESUME_PHONE_KEY=<passphrase> uv run build.py encrypt-phone
```

(In PowerShell, set `$env:RESUME_PHONE_KEY` first. Without the variable the helper asks for the passphrase.) Building needs the same passphrase in `RESUME_PHONE_KEY`: for the deployed page, add it as the repository secret `RESUME_PHONE_KEY`. If the variable is missing or wrong, the build warns and leaves the phone number out.

`resumes/` is generated and not committed; the GitHub Pages workflow builds and deploys it on every push to `main`.
