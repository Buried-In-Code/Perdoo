# Perdoo

[![PyPI - Python](https://img.shields.io/pypi/pyversions/Perdoo.svg?logo=PyPI&label=Python&style=flat-square)](https://pypi.python.org/pypi/Perdoo/)
[![PyPI - Status](https://img.shields.io/pypi/status/Perdoo.svg?logo=PyPI&label=Status&style=flat-square)](https://pypi.python.org/pypi/Perdoo/)
[![PyPI - Version](https://img.shields.io/pypi/v/Perdoo.svg?logo=PyPI&label=Version&style=flat-square)](https://pypi.python.org/pypi/Perdoo/)
[![PyPI - License](https://img.shields.io/pypi/l/Perdoo.svg?logo=PyPI&label=License&style=flat-square)](https://opensource.org/licenses/MIT)

[![Pre-Commit](https://img.shields.io/badge/pre--commit-enabled-informational?logo=pre-commit&style=flat-square)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/badge/ruff-enabled-informational?logo=ruff&style=flat-square)](https://github.com/astral-sh/ruff)

[![Github - Contributors](https://img.shields.io/github/contributors/Buried-In-Code/Perdoo.svg?logo=Github&label=Contributors&style=flat-square)](https://github.com/Buried-In-Code/Perdoo/graphs/contributors)

Perdoo is designed to assist in sorting and organizing your comic collection by utilizing metadata files stored within comic archives.\
Perdoo standardizes all your digital comics into a unified format (cb7, cbt, or cbz).\
It adds and/or updates metadata files using supported services.\
Unlike other tagging tools, Perdoo employs a manual approach when metadata files are absent, prompting users to enter the necessary Publisher/Series/Issue details for search purposes.

## Installation

### Pipx

1. Ensure you have [Pipx](https://pipx.pypa.io/stable/) installed: `pipx --version`
2. Install the project: `pipx install perdoo`

## Usage

<details><summary>Perdoo Commands</summary>

  <!-- RICH-CODEX hide_command: true -->
  ![`uv run Perdoo --help`](docs/img/perdoo-commands.svg)

</details>
<details><summary>Perdoo import</summary>

  <!-- RICH-CODEX hide_command: true -->
  ![`uv run Perdoo import --help`](docs/img/perdoo-import.svg)

</details>

### Perdoo archive Commands

<details><summary>Perdoo archive view</summary>

  <!-- RICH-CODEX hide_command: true -->
  ![`uv run Perdoo archive view --help`](docs/img/perdoo-archive-view.svg)

</details>

### Perdoo settings Commands

<details><summary>Perdoo settings view</summary>

  <!-- RICH-CODEX hide_command: true -->
  ![`uv run Perdoo settings view --help`](docs/img/perdoo-settings-view.svg)

</details>
<details><summary>Perdoo settings locate</summary>

  <!-- RICH-CODEX hide_command: true -->
  ![`uv run Perdoo settings locate --help`](docs/img/perdoo-settings-locate.svg)

</details>
<details><summary>Perdoo settings update</summary>

  <!-- RICH-CODEX hide_command: true -->
  ![`uv run Perdoo settings update --help`](docs/img/perdoo-settings-update.svg)

</details>

## Supported Formats

### Input Extensions

- .cbr
- .cbt
- .cbz
- .cb7 _(Requires installing `cb7` dependencies: `pipx install perdoo[cb7]`)_

### Output Extensions

- .cbt
- .cbz _(Default)_
- .cb7 _(Requires installing `cb7` dependencies: `pipx install perdoo[cb7]`)_

### Metadata Files

- [MetronInfo.xml](https://github.com/Metron-Project/metroninfo)
- Perdoo supports a slightly modified [ComicInfo.xml](https://github.com/anansi-project/comicinfo) to ignore field ordering.

## Services

- [Comicvine](https://comicvine.gamespot.com) using the [Simyan](https://github.com/Metron-Project/Simyan) library.
- [Marvel](https://www.marvel.com/comics) using the [Esak](https://github.com/Metron-Project/Esak) library.
- [Metron](https://metron.cloud) using the [Mokkari](https://github.com/Metron-Project/Mokkari) library.

## File Renaming and Organization

File naming and organization uses a pattern-based approach, it tries to name based on the MetronInfo data with a fallback to ComicInfo.

### Defaults

**MetronInfo Patterns**

- **_Default_**: `{publisher-name}/{series-name}-v{series-volume}/{series-name}-v{series-volume}_#{number:3}`
- Annual: `{publisher-name}/{series-name}-v{series-volume}/{series-name}-v{series-volume}_Annual_#{number:2}`
- Digital Chapter: `{publisher-name}/{series-name}-v{series-volume}/{series-name}-v{series-volume}_Chapter_#{number:3}`
- Graphic Novel: `{publisher-name}/{series-name}-v{series-volume}/{series-name}-v{series-volume}_#{number:2}_GN`
- Hardcover: `{publisher-name}/{series-name}-v{series-volume}/{series-name}-v{series-volume}_#{number:2}_HC`
- Omnibus: `{publisher-name}/{series-name}-v{series-volume}/{series-name}-v{series-volume}_#{number:2}_OB`
- Trade Paperback: `{publisher-name}/{series-name}-v{series-volume}/{series-name}-v{series-volume}_#{number:2}_TPB`

**ComicInfo Patterns**

- **_Default_**: `{publisher}/{series}-v{volume}/{series}-v{volume}_#{number:3}`

### Options

- **Padding**: Integer fields, such as `{number}`, can include optional zero-padding by specifying the width (e.g. `{number:3}` for three digits).
- **Sanitization**: All metadata values are sanitized to remove characters outside the set `0-9a-zA-Z&!-`. Custom characters can still be added directly to patterns.

**MetronInfo Placeholders**

| Pattern Key            | Description                                                       |
| ---------------------- | ----------------------------------------------------------------- |
| `{publisher-id}`       | The publisher's unique id.                                        |
| `{publisher-imprint}`  | The publisher's imprint.                                          |
| `{publisher-name}`     | The full name of the publisher.                                   |
| `{series-format}`      | The full format name of the series.                               |
| `{series-fmt}`         | Short format name (`Annual`, `Chapter`, `GN`, `HC`, `OB`, `TPB`). |
| `{series-id}`          | The series' unique id.                                            |
| `{series-issue-count}` | The total number of issues in the series.                         |
| `{series-lang}`        | The 2-letter language code.                                       |
| `{series-name}`        | The full name of the series.                                      |
| `{series-sort-name}`   | Sort-friendly name (omits leading "The", "A", etc...).            |
| `{series-year}`        | The year the series started.                                      |
| `{series-volume}`      | The volume of the series.                                         |
| `{title}`              | The issue title.                                                  |
| `{cover-date}`         | The issue cover date in `yyyy-mm-dd` format.                      |
| `{cover-year}`         | The year from the issue cover date.                               |
| `{cover-month}`        | The month from the issue cover date.                              |
| `{cover-day}`          | The day from the issue cover date.                                |
| `{id}`                 | The primary id of the issue.                                      |
| `{number}`             | The issue number.                                                 |
| `{store-date}`         | The store date of the issue in `yyyy-mm-dd` format.               |
| `{store-year}`         | The year from the issue store date.                               |
| `{store-month}`        | The month from the issue store date.                              |
| `{store-day}`          | The day from the issue store date.                                |
| `{gtin-isbn}`          | The issue's ISBN.                                                 |
| `{gtin-upc}`           | The issue's UPC.                                                  |

**ComicInfo Placeholders**

| Pattern Key    | Description                               |
| -------------- | ----------------------------------------- |
| `{count}`      | The total number of issues in the series. |
| `{cover-date}` | Issue cover date in `yyyy-mm-dd` format.  |
| `{year}`       | The year from the issue cover date.       |
| `{month}`      | The month from the issue cover date.      |
| `{day}`        | The day from the issue cover date.        |
| `{format}`     | The full format name of the issue.        |
| `{imprint}`    | The publisher's imprint.                  |
| `{lang}`       | The 2-letter language code.               |
| `{number}`     | The issue number.                         |
| `{publisher}`  | The full name of the publisher.           |
| `{series}`     | The full name of the series.              |
| `{title}`      | The issue title.                          |
| `{volume}`     | The volume of the series.                 |

## Socials

[![Social - Fosstodon](https://img.shields.io/badge/%40BuriedInCode-teal?label=Fosstodon&logo=mastodon&style=for-the-badge)](https://fosstodon.org/@BuriedInCode)\
[![Social - Matrix](https://img.shields.io/matrix/The-Dev-Environment:matrix.org?label=The-Dev-Environment&logo=matrix&style=for-the-badge)](https://matrix.to/#/#The-Dev-Environment:matrix.org)
