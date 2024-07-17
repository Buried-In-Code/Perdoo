# Perdoo

[![PyPI - Python](https://img.shields.io/pypi/pyversions/Perdoo.svg?logo=PyPI&label=Python&style=flat-square)](https://pypi.python.org/pypi/Perdoo/)
[![PyPI - Status](https://img.shields.io/pypi/status/Perdoo.svg?logo=PyPI&label=Status&style=flat-square)](https://pypi.python.org/pypi/Perdoo/)
[![PyPI - Version](https://img.shields.io/pypi/v/Perdoo.svg?logo=PyPI&label=Version&style=flat-square)](https://pypi.python.org/pypi/Perdoo/)
[![PyPI - License](https://img.shields.io/pypi/l/Perdoo.svg?logo=PyPI&label=License&style=flat-square)](https://opensource.org/licenses/MIT)

[![Rye](https://img.shields.io/badge/Rye-informational?style=flat-square&logo=rye&labelColor=grey)](https://rye.astral.sh)
[![Pre-Commit](https://img.shields.io/badge/Pre--Commit-informational?style=flat-square&logo=pre-commit&labelColor=grey)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/badge/Ruff-informational?style=flat-square&logo=ruff&labelColor=grey)](https://github.com/astral-sh/ruff)

[![Github - Contributors](https://img.shields.io/github/contributors/Buried-In-Code/Perdoo.svg?logo=Github&label=Contributors&style=flat-square)](https://github.com/Buried-In-Code/Perdoo/graphs/contributors)

Perdoo is designed to assist in sorting and organizing your comic collection by utilizing metadata files stored within comic archives.\
Perdoo standardizes all your digital comics into a unified format (cb7, cbt, or cbz).\
It adds and/or updates metadata files using supported services.\
Unlike other tagging tools, Perdoo employs a manual approach when metadata files are absent, prompting users to enter the necessary Publisher/Series/Issue details for search purposes.

## Installation

### Pipx

1. Ensure you have [Pipx](https://pipxproject.github.io/pipx/) installed: `pipx --version`
2. Install the project: `pipx install perdoo`

### From Source

1. Ensure you have a supported version of [Python](https://www.python.org/) installed: `python --version`
2. Clone the repository: `git clone https://github.com/Buried-In-Code/Perdoo`
3. Install the project: `pip install .`

## Execution

- `Perdoo <arguments>`

### Arguments

| Argument    | Type | Description                                                             |
| ----------- | ---- | ----------------------------------------------------------------------- |
| `--force`   | bool | Forces the sync of archives, regardless of when they were last updated. |
| `--version` | bool | Displays the version of Perdoo running.                                 |
| `--debug`   | bool | Displays extra/debug messages while running.                            |

## Supported Formats

### Input Extensions

- .cbr
- .cbt
- .cbz
- .cb7 _(Requires installing `cb7` dependencies: `pip install perdoo[cb7]`)_

### Output Extensions

- .cbt
- .cbz _(Default)_
- .cb7 _(Requires installing `cb7` dependencies: `pip install perdoo[cb7]`)_

### Metadata Files

- [Metadata.xml](https://github.com/Buried-In-Code/Schemas)
- [MetronInfo.xml](https://github.com/Metron-Project/metroninfo)
- Perdoo supports a slightly modified [ComicInfo.xml](https://github.com/anansi-project/comicinfo) to ignore field ordering. _See [Buried-In-Code/Schemas](https://github.com/Buried-In-Code/Schemas) for details._

## Services

- [Comicvine](https://comicvine.gamespot.com) using the [Simyan](https://github.com/Metron-Project/Simyan) library.
- [League of Comic Geeks](https://leagueofcomicgeeks.com) using the [Himon](https://github.com/Buried-In-Code/Himon) library.
- [Marvel](https://www.marvel.com/comics) using the [Esak](https://github.com/Metron-Project/Esak) library.
- [Metron](https://metron.cloud) using the [Mokkari](https://github.com/Metron-Project/Mokkari) library.

## File Organization

### Series Naming

Series with a volume greater than 1 will display its volume in the title.

### Comic Naming

The files are named based on the format of the comic:

- **_Default/Comic_**: `{Series Title}_#{Issue Number}.cbz`
- Annual: `{Series Title}_Annual_#{Issue Number}.cbz`
- Digital Chapter: `{Series Title}_Chapter_#{Issue Number}.cbz`
- Hardcover: `{Series Title}_#{Issue Number}_HC.cbz`
- Trade Paperback: `{Series Title}_#{Issue Number}_TP.cbz`
- Graphic Novel: `{Series Title}_#{Issue Number}_GN.cbz`

## Collection Folder Structure

```
Collection Root
+-- Publisher
|  +-- Series
|  |  +-- Series_#001.cbz
|  |  +-- Series_Annual_#01.cbz
|  |  +-- Series_Chapter_#01.cbz
|  |  +-- Series_#01_HC.cbz
|  |  +-- Series_#01_TP.cbz
|  |  +-- Series_#01_GN.cbz
|  +-- Series-v2
|  |  +-- Series-v2_#001.cbz
|  |  +-- Series-v2_Annual_#01.cbz
|  |  +-- Series-v2_Chapter_#01.cbz
|  |  +-- Series-v2_#01_HC.cbz
|  |  +-- Series-v2_#01_TP.cbz
|  |  +-- Series-v2_#01_GN.cbz
```

## Socials

[![Social - Fosstodon](https://img.shields.io/badge/%40BuriedInCode-teal?label=Fosstodon&logo=mastodon&style=for-the-badge)](https://fosstodon.org/@BuriedInCode)\
[![Social - Matrix](https://img.shields.io/matrix/The-Dev-Environment:matrix.org?label=The-Dev-Environment&logo=matrix&style=for-the-badge)](https://matrix.to/#/#The-Dev-Environment:matrix.org)
