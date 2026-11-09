import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

import jinja2

ROOT = Path(__file__).parent
RESUME_DATA_PATH = ROOT / "resume.json"
TEMPLATES_DIR = ROOT / "templates"
TEMPLATE_NAME = "template.html"
OUTPUT_PATH = ROOT / "resumes" / "index.html"  # index.html so that GitHub Pages serves it

# Browsers that can print the page to PDF, looked up on PATH in this order.
BROWSER_COMMANDS = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"]
BROWSER_WINDOWS_PATHS = [
    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
    r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
    r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
    r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
]


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


def pdf_filename(data: dict) -> str:
    """Name the PDF after the person, e.g. "Lukáš Nedbálek" -> "lukas-nedbalek-resume.pdf"."""
    name = unicodedata.normalize("NFKD", data.get("basics", {}).get("name", ""))
    slug = re.sub(r"[^a-z0-9]+", "-", name.encode("ascii", "ignore").decode().lower()).strip("-")
    return f"{slug}-resume.pdf" if slug else "resume.pdf"


def find_browser() -> str | None:
    """Locate a Chrome/Chromium/Edge binary: RESUME_BROWSER first, then PATH, then known Windows locations."""
    override = os.environ.get("RESUME_BROWSER")
    if override:
        return override if shutil.which(override) else None
    for command in BROWSER_COMMANDS:
        if found := shutil.which(command):
            return found
    for template in BROWSER_WINDOWS_PATHS:
        path = Path(os.path.expandvars(template))
        if path.is_file():
            return str(path)
    return None


def build_pdf(html_path: Path, pdf_path: Path) -> bool:
    """Print html_path to pdf_path with headless Chrome/Edge. Returns whether the PDF was written."""
    browser = find_browser()
    if browser is None:
        print("warning: no Chrome/Chromium/Edge found (set RESUME_BROWSER to its path); PDF skipped", file=sys.stderr)
        return False

    pdf_path.unlink(missing_ok=True)
    # A throwaway profile so this never collides with a browser the user already has open.
    with tempfile.TemporaryDirectory() as profile:
        command = [
            browser,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--user-data-dir={profile}",
            f"--print-to-pdf={pdf_path}",
            html_path.resolve().as_uri(),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, timeout=60)
        except (subprocess.SubprocessError, OSError) as error:
            print(f"warning: PDF generation with {browser} failed ({error}); PDF skipped", file=sys.stderr)
            return False
    if not pdf_path.is_file():
        print(f"warning: {browser} produced no PDF; PDF skipped", file=sys.stderr)
        return False
    return True


def build() -> None:
    data = json.loads(RESUME_DATA_PATH.read_text(encoding="utf-8"))

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
        autoescape=jinja2.select_autoescape(["html"]),
    )
    template = env.get_template(TEMPLATE_NAME)
    skill_groups = group_skills(data)
    pdf_name = pdf_filename(data)
    pdf_path = OUTPUT_PATH.with_name(pdf_name)

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    # First render links to the PDF (hidden in print, so the PDF is the same either way);
    # if the PDF could not be made, render again without the link.
    OUTPUT_PATH.write_text(template.render(**data, skill_groups=skill_groups, pdf_url=pdf_name), encoding="utf-8")
    print(f"Built {OUTPUT_PATH.relative_to(ROOT)}")

    if build_pdf(OUTPUT_PATH, pdf_path):
        print(f"Built {pdf_path.relative_to(ROOT)}")
    else:
        OUTPUT_PATH.write_text(template.render(**data, skill_groups=skill_groups, pdf_url=None), encoding="utf-8")


if __name__ == "__main__":
    build()
