import json
import sys
from pathlib import Path

import jinja2

ROOT = Path(__file__).parent
RESUME_DATA_PATH = ROOT / "resume.json"
TEMPLATES_DIR = ROOT / "templates"
TEMPLATE_NAME = "template.html"
OUTPUT_PATH = ROOT / "resumes" / "index.html"  # index.html so that GitHub Pages serves it


def group_skills(data: dict) -> list[tuple[str, list[dict]]]:
    """Group skills by level, in the order given by meta.skillLevels.

    Each skill is a dict with its name and keywords (possibly empty).
    A skill whose level is missing or not in that list is omitted with a warning.
    """
    groups: dict[str, list[dict]] = {level: [] for level in data.get("meta", {}).get("skillLevels", [])}
    for skill in data.get("skills", []):
        name, level = skill.get("name"), skill.get("level")
        if name and level in groups:
            groups[level].append({"name": name, "keywords": skill.get("keywords", [])})
        else:
            print(f"warning: skill {name!r} has a missing name or a missing/unknown level {level!r}; omitted", file=sys.stderr)
    return [(level, skills) for level, skills in groups.items() if skills]


def build() -> None:
    data = json.loads(RESUME_DATA_PATH.read_text(encoding="utf-8"))

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
        autoescape=jinja2.select_autoescape(["html"]),
    )
    output = env.get_template(TEMPLATE_NAME).render(**data, skill_groups=group_skills(data))

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(output, encoding="utf-8")
    print(f"Built {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
