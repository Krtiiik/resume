import json
from pathlib import Path

import jinja2

ROOT = Path(__file__).parent
RESUME_DATA_PATH = ROOT / "resume.json"
TEMPLATES_DIR = ROOT / "templates"
TEMPLATE_NAME = "template.html"
OUTPUT_PATH = ROOT / "resumes" / "index.html"  # index.html so that GitHub Pages serves it


def build() -> None:
    data = json.loads(RESUME_DATA_PATH.read_text(encoding="utf-8"))

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
        autoescape=jinja2.select_autoescape(["html"]),
    )
    output = env.get_template(TEMPLATE_NAME).render(**data)

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(output, encoding="utf-8")
    print(f"Built {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
