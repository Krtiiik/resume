# Resume

This is my resume, published at <https://krtiiik.github.io/resume/>.

The data lives in `resume.json` ([JSON Resume](https://www.jsonresume.org/) format), the layout and styling in `templates/` (`template.html`, with `style.css` inlined into it). The build renders them into a single self-contained `resumes/index.html` (the Source Serif 4 font is embedded from `templates/fonts/`), then prints it to a PDF named after the person (e.g. `resumes/lukas-nedbalek-resume.pdf`):

```
uv run build.py
```

The PDF is made by headless Chrome, Chromium or Edge, found on `PATH` or in the usual Windows install folders; set `RESUME_BROWSER` to a browser executable to override this. Without a browser the PDF is skipped with a warning and the page omits its PDF link.

`resumes/` is generated and not committed; the GitHub Pages workflow builds and deploys it on every push to `main`.
