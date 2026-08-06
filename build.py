import json
import os
from pathlib import Path
import jinja2


RESUME_DATA_PATH = Path("resume.json")
TEMPLATES_DIR = Path("templates")
TEMPLATE_FMT = "template.{format}"
RESUMES_DIR = Path("resumes")
RESUME_FMT = "resume.{format}"


with open(RESUME_DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_DIR))

os.makedirs(RESUMES_DIR, exist_ok=True)
for format in ["html", "tex"]:
    try:
        template = env.get_template(TEMPLATE_FMT.format(format=format))
    except jinja2.TemplateNotFound:
        print(f"! Template for [{format}] format does not exist in \"{str(TEMPLATES_DIR)}\"")
        continue

    output = template.render(**data)
    resume_path = RESUMES_DIR / RESUME_FMT.format(format=format)
    with open(resume_path, "w", encoding="utf-8") as f:
        f.write(output)
