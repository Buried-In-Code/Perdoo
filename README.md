# Perdoo

[![PyPI - Python](https://img.shields.io/pypi/pyversions/Perdoo.svg?logo=PyPI&label=Python&style=flat-square)](https://pypi.python.org/pypi/Perdoo/)
[![PyPI - Status](https://img.shields.io/pypi/status/Perdoo.svg?logo=PyPI&label=Status&style=flat-square)](https://pypi.python.org/pypi/Perdoo/)
[![PyPI - Version](https://img.shields.io/pypi/v/Perdoo.svg?logo=PyPI&label=Version&style=flat-square)](https://pypi.python.org/pypi/Perdoo/)
[![PyPI - License](https://img.shields.io/pypi/l/Perdoo.svg?logo=PyPI&label=License&style=flat-square)](https://opensource.org/licenses/MIT)

[![Pre-Commit](https://img.shields.io/badge/pre--commit-enabled-informational?logo=pre-commit&style=flat-square)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/badge/ruff-enabled-informational?logo=ruff&style=flat-square)](https://github.com/astral-sh/ruff)

[![Github - Contributors](https://img.shields.io/github/contributors/Buried-In-Code/Perdoo.svg?logo=Github&label=Contributors&style=flat-square)](https://github.com/Buried-In-Code/Perdoo/graphs/contributors)
[![Github Action - Testing](https://img.shields.io/github/actions/workflow/status/Buried-In-Code/Perdoo/testing.yaml?branch=main&logo=Github&label=Testing&style=flat-square)](https://github.com/Buried-In-Code/Perdoo/actions/workflows/testing.yaml)
[![Github Action - Publishing](https://img.shields.io/github/actions/workflow/status/Buried-In-Code/Perdoo/publishing.yaml?branch=main&logo=Github&label=Publishing&style=flat-square)](https://github.com/Buried-In-Code/Perdoo/actions/workflows/publishing.yaml)


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
Naming is done based on the Comic Format, set the value to `""` and it will fallback to the default setting.

- **_Default_**: `{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_#{number:3}`
- **Annual**: `{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_Annual_#{number:2}`
- **Digital Chapter**: `{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_Chapter_#{number:3}`
- **Graphic Novel**: `{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_GN_#{number:2}`
- **Hardcover**: `{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_HC_#{number:2}`
- **Limited Series**: `""` _Falls back to Default_
- **Omnibus**: `{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_OB_#{number:2}`
- **One-Shot**: `""` _Falls back to Default_
- **Single Issue**: `""` _Falls back to Default_
- **Trade Paperback**: `{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_TPB_#{number:2}`

### Options

- **Padding**: Int and Int-like fields, such as `{number}`, can include optional zero-padding by specifying the length (e.g. `{number:3}` will pad 0's to be atleast 3 digits long, `12` => `012`).
- **Sanitization**: All metadata values are sanitized to remove characters outside the set `0-9a-zA-Z&!-`. Custom characters can still be added directly to patterns.

| Pattern Key          | Description                                            |
| -------------------- | ------------------------------------------------------ |
| `{cover-date}`       | The issue cover date in `yyyy-mm-dd` format.           |
| `{cover-day}`        | The day from the issue cover date.                     |
| `{cover-month}`      | The month from the issue cover date.                   |
| `{cover-year}`       | The year from the issue cover date.                    |
| `{format}`           | The full format name of the series.                    |
| `{id}`               | The primary id of the issue.                           |
| `{imprint}`          | The publisher's imprint.                               |
| `{isbn}`             | The issue's ISBN.                                      |
| `{issue-count}`      | The total number of issues in the series.              |
| `{lang}`             | The issue's language.                                  |
| `{number}`           | The issue number.                                      |
| `{publisher-id}`     | The publisher's unique id.                             |
| `{publisher-name}`   | The full name of the publisher.                        |
| `{series-id}`        | The series' unique id.                                 |
| `{series-name}`      | The full name of the series.                           |
| `{series-sort-name}` | Sort-friendly name (omits leading "The", "A", etc...). |
| `{series-year}`      | The year the series started.                           |
| `{store-date}`       | The store date of the issue in `yyyy-mm-dd` format.    |
| `{store-day}`        | The day from the issue store date.                     |
| `{store-month}`      | The month from the issue store date.                   |
| `{store-year}`       | The year from the issue store date.                    |
| `{title}`            | The issue title.                                       |
| `{upc}`              | The issue's UPC.                                       |
| `{volume}`           | The volume of the series.                              |

## Socials

[![Social - Fosstodon](https://img.shields.io/badge/%40BuriedInCode-teal?label=Fosstodon&logo=mastodon&style=for-the-badge)](https://fosstodon.org/@BuriedInCode)\
[![Social - Matrix](https://img.shields.io/matrix/The-Dev-Environment:matrix.org?label=The-Dev-Environment&logo=matrix&style=for-the-badge)](https://matrix.to/#/#The-Dev-Environment:matrix.org)
