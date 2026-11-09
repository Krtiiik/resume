# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Languages section, and work entry highlights (e.g. the Shift Manager Course), which were in `resume.json` but not rendered.

### Changed

- The resume is now a single self-contained `index.html` with the stylesheet inlined; the GitHub Pages workflow builds it instead of deploying a committed copy.
- Publication dates use the same `YYYY/MM/DD` style as the other entries.

### Fixed

- Mismatched `<h4>`/`</h3>` tags in work entries, and an empty paragraph under publications.
- GitHub Pages deploy failing because `astral-sh/setup-uv@v10` does not exist; pinned to `v10.3.3` (setup-uv publishes no floating major tag past `v7`).
- Dropped the unused Font Awesome stylesheet and the dangling `photo.jpg` reference.
