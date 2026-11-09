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
- Dropped the unused Font Awesome stylesheet and the dangling `photo.jpg` reference.
