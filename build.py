import base64
import getpass
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

import jinja2
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).parent
RESUME_DATA_PATH = ROOT / "resume.json"
TEMPLATES_DIR = ROOT / "templates"
TEMPLATE_NAME = "template.html"
FONTS_DIR = TEMPLATES_DIR / "fonts"
OUTPUT_PATH = ROOT / "resumes" / "index.html"  # index.html so that GitHub Pages serves it

# Source Serif 4 (variable weight), inlined into the page. Each subset covers its unicode-range only,
# so the browser uses the latin-ext file just for characters such as the "š" in the name.
FONT_FAMILY = "Source Serif 4"
FONT_SUBSETS = {
    "latin": "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,"
    "U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD",
    "latin-ext": "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,"
    "U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF",
}

# basics.phone in resume.json is stored encrypted (see encrypt_phone) so that scrapers reading the public repo
# or the page cannot pick it up. The passphrase comes from this environment variable, e.g. a GitHub Actions secret.
PHONE_KEY_ENV = "RESUME_PHONE_KEY"
PHONE_FONT = FONTS_DIR / "source-serif-4-latin-wght-normal.woff2"

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


def font_face_css() -> str:
    """@font-face rules with the fonts in templates/fonts embedded as base64, so the page needs no network."""
    rules = []
    for style in ("normal", "italic"):
        for subset, unicode_range in FONT_SUBSETS.items():
            font = FONTS_DIR / f"source-serif-4-{subset}-wght-{style}.woff2"
            encoded = base64.b64encode(font.read_bytes()).decode("ascii")
            rules.append(
                f'@font-face {{ font-family: "{FONT_FAMILY}"; font-style: {style}; font-weight: 200 900; '
                f"font-display: swap; src: url(data:font/woff2;base64,{encoded}) format('woff2'); "
                f"unicode-range: {unicode_range}; }}"
            )
    return "\n".join(rules)


def photo_data_uri(data: dict) -> str | None:
    """basics.image (a path relative to the project root) as a base64 data URI, so the page stays self-contained.

    Returns None, with a warning if an image was named, when there is no usable image.
    """
    name = data.get("basics", {}).get("image")
    if not name:
        return None
    path = ROOT / name
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(path.suffix.lower())
    if mime is None or not path.is_file():
        print(f"warning: basics.image {name!r} is not a readable jpg, png or webp file; photo omitted", file=sys.stderr)
        return None
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _derive_keys(passphrase: str, salt: bytes) -> tuple[bytes, bytes]:
    """Stretch the passphrase into an encryption key and a separate authentication key."""
    material = hashlib.scrypt(passphrase.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
    return material[:32], material[32:]


def _xor_keystream(key: bytes, data: bytes) -> bytes:
    """XOR data with an HMAC-SHA256 counter-mode keystream (the same call encrypts and decrypts)."""
    stream = b"".join(hmac.new(key, counter.to_bytes(4, "big"), "sha256").digest() for counter in range(len(data) // 32 + 1))
    return bytes(a ^ b for a, b in zip(data, stream))


def encrypt_phone(phone: str, passphrase: str) -> str:
    """Encrypt a phone number into a URL-safe string for basics.phone in resume.json.

    The string is base64 of salt | ciphertext | tag, with a fresh random salt each time, so it reveals nothing
    about the number except its length, and a wrong passphrase or a tampered string is detected on decryption.
    """
    salt = secrets.token_bytes(16)
    enc_key, mac_key = _derive_keys(passphrase, salt)
    cipher = _xor_keystream(enc_key, phone.encode("utf-8"))
    tag = hmac.new(mac_key, salt + cipher, "sha256").digest()[:16]
    return base64.urlsafe_b64encode(salt + cipher + tag).decode("ascii")


def decrypt_phone(token: str, passphrase: str) -> str:
    """Inverse of encrypt_phone. Raises ValueError for a malformed string or a wrong passphrase."""
    raw = base64.urlsafe_b64decode(token)
    if len(raw) < 33:
        raise ValueError("the encrypted phone number is malformed")
    salt, cipher, tag = raw[:16], raw[16:-16], raw[-16:]
    enc_key, mac_key = _derive_keys(passphrase, salt)
    if not hmac.compare_digest(tag, hmac.new(mac_key, salt + cipher, "sha256").digest()[:16]):
        raise ValueError("wrong passphrase or corrupted phone number")
    return _xor_keystream(enc_key, cipher).decode("utf-8")


def phone_to_svg(phone: str) -> str:
    """Draw the phone number as an SVG of glyph outlines from the page font, so no text for scrapers (or PDF
    text extraction) to find. It is filled with currentColor and sized in em, so it follows the surrounding text."""
    font = TTFont(PHONE_FONT)
    glyph_set, cmap, advances = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    units = font["head"].unitsPerEm
    ascent, descent = font["hhea"].ascent, -font["hhea"].descent

    outlines, x = [], 0
    for char in phone:
        name = cmap.get(ord(char))
        if name is None:
            raise ValueError(f"the font has no glyph for {char!r} in the phone number")
        pen = SVGPathPen(glyph_set)
        glyph_set[name].draw(TransformPen(pen, (1, 0, 0, -1, x, 0)))  # y points down in SVG; baseline at y = 0
        outlines.append(pen.getCommands())
        x += advances[name][0]

    return (
        f'<svg class="brand phone" viewBox="0 {-ascent} {x} {ascent + descent}" role="img" aria-label="Phone number" '
        f'style="width: {x / units:.3f}em; height: {(ascent + descent) / units:.3f}em"><path d="{" ".join(outlines)}"/></svg>'
    )


def render_phone(data: dict) -> str | None:
    """The decrypted basics.phone as SVG, or None (with a warning if there was a number) when it can't be shown."""
    token = data.get("basics", {}).get("phone")
    if not token:
        return None
    passphrase = os.environ.get(PHONE_KEY_ENV)
    if not passphrase:
        print(f"warning: basics.phone is set but {PHONE_KEY_ENV} is not; phone number omitted", file=sys.stderr)
        return None
    try:
        return phone_to_svg(decrypt_phone(token, passphrase))
    except ValueError as error:
        print(f"warning: {error}; phone number omitted", file=sys.stderr)
        return None


def encrypt_phone_command() -> None:
    """Interactive helper: ask for the phone number and print the string to put in basics.phone."""
    passphrase = os.environ.get(PHONE_KEY_ENV)
    if not passphrase:
        passphrase = getpass.getpass(f"{PHONE_KEY_ENV} is not set; passphrase to encrypt with: ")
        if getpass.getpass("Repeat passphrase: ") != passphrase:
            sys.exit("error: the passphrases differ")
    phone = input("Phone number, as it should appear on the resume: ").strip()
    if not phone or not passphrase:
        sys.exit("error: need both a phone number and a passphrase")
    phone_to_svg(phone)  # fails early if the font can't draw some character
    print('\nPut this in resume.json, as "phone" inside "basics":\n')
    print(encrypt_phone(phone, passphrase))


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
    font_css = font_face_css()
    phone_svg = render_phone(data)
    photo_uri = photo_data_uri(data)
    pdf_name = pdf_filename(data)
    pdf_path = OUTPUT_PATH.with_name(pdf_name)

    def render(pdf_url: str | None) -> str:
        return template.render(
            **data, skill_groups=skill_groups, font_css=font_css, phone_svg=phone_svg, photo_uri=photo_uri, pdf_url=pdf_url
        )

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    # First render links to the PDF (hidden in print, so the PDF is the same either way);
    # if the PDF could not be made, render again without the link.
    OUTPUT_PATH.write_text(render(pdf_name), encoding="utf-8")
    print(f"Built {OUTPUT_PATH.relative_to(ROOT)}")

    if build_pdf(OUTPUT_PATH, pdf_path):
        print(f"Built {pdf_path.relative_to(ROOT)}")
    else:
        OUTPUT_PATH.write_text(render(None), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        build()
    elif sys.argv[1:] == ["encrypt-phone"]:
        encrypt_phone_command()
    else:
        sys.exit("usage: build.py [encrypt-phone]")
