from pathlib import Path

from perdoo.archives import CB7Archive, CBTArchive, CBZArchive, get_archive
from perdoo.settings import OutputFormat


def convert_files(files: list[Path], output_format: OutputFormat) -> None:
    archive_type = {OutputFormat.CB7: CB7Archive, OutputFormat.CBT: CBTArchive}.get(
        output_format, CBZArchive
    )
    for entry in files:
        archive = get_archive(path=entry)
        archive_type.convert(old_archive=archive)
