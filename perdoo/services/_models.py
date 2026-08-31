__all__ = ["MetadataResult", "Search"]

from dataclasses import dataclass

from comicfn2dict import comicfn2dict
from shortbox import Comic
from shortbox.metadata import ComicInfo, MetronInfo
from shortbox.metadata.metron_info import Id, InformationSource


@dataclass(frozen=True)
class MetadataResult:
    comic_info: ComicInfo
    metron_info: MetronInfo


@dataclass
class SeriesSearch:
    name: str
    volume: int | None = None
    year: int | None = None
    comicvine: int | None = None
    metron: int | None = None


@dataclass
class IssueSearch:
    number: str | None = None
    comicvine: int | None = None
    metron: int | None = None


@dataclass
class Search:
    series: SeriesSearch
    issue: IssueSearch
    filename: str

    @staticmethod
    def build(comic: Comic) -> "Search":
        if (
            (metron_info := comic.get_metadata(MetronInfo))
            and metron_info.series
            and metron_info.series.name
        ):
            return search_from_metron_info(metadata=metron_info, filename=comic.file.stem)
        if (comic_info := comic.get_metadata(ComicInfo)) and comic_info.series:
            return search_from_comic_info(metadata=comic_info, filename=comic.file.stem)
        return search_from_filename(filename=comic.file.stem)


def get_id(ids: list[Id], source: InformationSource) -> str | None:
    return next((x.value for x in ids if x.source is source), None)


def search_from_metron_info(metadata: MetronInfo, filename: str) -> Search:
    series_id = metadata.series.id
    comicvine_id = get_id(metadata.ids, InformationSource.COMIC_VINE)
    metron_id = get_id(metadata.ids, InformationSource.METRON)
    source = next((x.source for x in metadata.ids if x.primary), None)
    return Search(
        series=SeriesSearch(
            name=metadata.series.name,
            volume=metadata.series.volume,
            year=metadata.series.start_year,
            comicvine=int(series_id)
            if series_id and source == InformationSource.COMIC_VINE
            else None,
            metron=int(series_id) if series_id and source == InformationSource.METRON else None,
        ),
        issue=IssueSearch(
            number=metadata.number,
            comicvine=int(comicvine_id) if comicvine_id else None,
            metron=int(metron_id) if metron_id else None,
        ),
        filename=filename,
    )


def search_from_comic_info(metadata: ComicInfo, filename: str) -> Search:
    volume = metadata.volume
    year = volume if volume and volume > 1900 else None
    volume = volume if volume and volume < 1900 else None
    return Search(
        series=SeriesSearch(name=metadata.series or filename, volume=volume, year=year),
        issue=IssueSearch(number=metadata.number),
        filename=filename,
    )


def search_from_filename(filename: str) -> Search:
    series_name = comicfn2dict(filename).get("series", filename)
    series_name = str(series_name).replace("-", " ")
    return Search(series=SeriesSearch(name=series_name), issue=IssueSearch(), filename=filename)
