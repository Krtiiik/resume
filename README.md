# Resume

This is my resume, published at <https://krtiiik.github.io/resume/>.

The data lives in `resume.json` ([JSON Resume](https://www.jsonresume.org/) format), the layout and styling in `templates/` (`template.html`, with `style.css` inlined into it). The build renders them into a single self-contained `resumes/index.html`:

```
uv run build.py
```

`resumes/` is generated and not committed; the GitHub Pages workflow builds and deploys it on every push to `main`.
