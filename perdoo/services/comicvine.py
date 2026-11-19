__all__ = ["Comicvine"]

import re
from datetime import datetime

from natsort import humansorted, ns
from questionary import Choice, confirm, text
from shortbox.metadata import ComicInfo, MetronInfo
from shortbox.metadata.metron_info import Format, InformationSource
from simyan.comicvine import Comicvine as Simyan
from simyan.errors import ServiceError
from simyan.schemas.issue import Issue
from simyan.schemas.volume import Volume

from perdoo import get_cache_home
from perdoo.console import CONSOLE
from perdoo.services._base import prompt_select
from perdoo.services._models import (
    IssueSearch,
    MetadataResult,
    Search,
    SeriesSearch,
    set_comic_info_note_id,
)


class Comicvine:
    def __init__(self, api_key: str, override_format: bool = False):
        self.session = Simyan(
            api_key=api_key,
            cache_path=get_cache_home() / "simyan.sqlite",
            ratelimit_path=get_cache_home() / "simyan-rates.sqlite",
        )
        self._override_format = override_format

    def _search_series(
        self, name: str | None, volume: int | None, year: int | None, filename: str
    ) -> int | None:
        name = name or text(message="Volume Name").ask()
        try:
            options = sorted(
                self.session.list_volumes({"filter": f"name:{name}"}),
                key=lambda x: (
                    x.publisher.name if x.publisher and x.publisher.name else "",
                    x.name,
                    x.start_year or 0,
                ),
            )
            if year:
                options = [x for x in options if x.start_year == year]
            if options:
                search = name
                if volume:
                    search += f" v{volume}"
                if year:
                    search += f" ({year})"
                choices = [
                    Choice(
                        title=[
                            (
                                "class:dim",
                                f"{x.id} | {x.publisher.name if x.publisher and x.publisher.name else ''} | ",  # noqa: E501
                            ),
                            ("class:title", f"{x.name} ({x.start_year})"),
                        ],
                        description=f"https://comicvine.gamespot.com/volumes/4050-{x.id}",
                        value=x,
                    )
                    for x in options
                ]
                selected = prompt_select(
                    message=f"Searching Comicvine for Volumes matching '{filename}'"
                    if not year
                    else f"Searching Comicvine for Volume '{search}'",
                    choices=choices,
                )
                if selected:
                    return selected.id
            else:
                CONSOLE.print(
                    f"Unable to find any Volumes on Comicvine for the file: {filename!r}",
                    style="logging.level.warning",
                )
            if year:
                CONSOLE.print("Searching again without the StartYear", style="logging.level.info")
                return self._search_series(name=name, volume=volume, year=None, filename=filename)
            if confirm(message="Search Again", default=False).ask():
                return self._search_series(name=None, volume=None, year=None, filename=filename)
        except ServiceError as err:
            CONSOLE.print(err, style="logging.level.error")
        return None

    def _fetch_series(self, search: SeriesSearch, filename: str) -> Volume | None:
        series_id = search.comicvine or self._search_series(
            name=search.name, volume=search.volume, year=search.year, filename=filename
        )
        if not series_id:
            return None
        try:
            series = self.session.get_volume(volume_id=series_id)
            search.comicvine = series_id
            return series
        except ServiceError as err:
            CONSOLE.print(err, style="logging.level.error")
        if search.comicvine:
            search.comicvine = None
            return self._fetch_series(search=search, filename=filename)
        return None

    def _search_issue(self, series_id: int, number: str | None, filename: str) -> int | None:
        try:
            options = humansorted(
                self.session.list_issues(
                    {"filter": f"volume:{series_id},issue_number:{number}"}
                    if number
                    else {"filter": f"volume:{series_id}"}
                ),
                key=lambda x: (x.number, x.name),
                alg=ns.NA | ns.G,
            )
            if options:
                choices = [
                    Choice(
                        title=[
                            ("class:dim", f"{x.id} | "),
                            ("class:title", f"{x.number} - {x.name or ''}"),
                        ],
                        description=f"https://comicvine.gamespot.com/issues/4000-{x.id}",
                        value=x,
                    )
                    for x in options
                ]
                selected = prompt_select(
                    message=f"Searching Comicvine for Issues matching {filename!r}"
                    if not number
                    else f"Searching Comicvine for Issues with number {number!r}",
                    choices=choices,
                )
                if selected:
                    return selected.id
            else:
                CONSOLE.print(
                    f"Unable to find any Issues on Comicvine for the file: {filename!r}",
                    style="logging.level.warning",
                )
            if number:
                CONSOLE.print("Searching again without the IssueNumber", style="logging.level.info")
                return self._search_issue(series_id=series_id, number=None, filename=filename)
        except ServiceError as err:
            CONSOLE.print(err, style="logging.level.error")
        return None

    def _fetch_issue(self, series_id: int, search: IssueSearch, filename: str) -> Issue | None:
        issue_id = search.comicvine or self._search_issue(
            series_id=series_id, number=search.number, filename=filename
        )
        if not issue_id:
            return None
        try:
            issue = self.session.get_issue(issue_id=issue_id)
            search.comicvine = issue_id
            return issue
        except ServiceError as err:
            CONSOLE.print(err, style="logging.level.error")
        if search.comicvine:
            search.comicvine = None
            return self._fetch_issue(series_id=series_id, search=search, filename=filename)
        return None

    def _build_metron_info(
        self, series: Volume, issue: Issue, format_: Format | None = None
    ) -> MetronInfo:
        from shortbox.metadata.metron_info import (  # noqa: PLC0415
            Arc,
            Credit,
            Id,
            Publisher,
            Resource,
            Role,
            Series,
            Url,
        )

        def load_role(value: str) -> Role:
            try:
                return Role.load(value=value.strip())
            except ValueError:
                return Role.OTHER

        return MetronInfo(
            arcs=[Arc(id=str(x.id), name=x.name) for x in issue.story_arcs if x.name],
            characters=[
                Resource[str](id=str(x.id), value=x.name) for x in issue.characters if x.name
            ],
            collection_title=issue.name,
            cover_date=issue.cover_date,
            credits=[
                Credit(
                    creator=Resource[str](id=str(x.id), value=x.name),
                    roles=[
                        Resource[Role](value=load_role(value=r.strip()))
                        for r in re.split(r"[~\r\n,]+", x.roles)
                        if r.strip()
                    ],
                )
                for x in issue.creators
                if x.name
            ],
            genres=[],
            ids=[Id(primary=True, source=InformationSource.COMIC_VINE, value=str(issue.id))],
            last_modified=datetime.now().astimezone(),
            locations=[
                Resource[str](id=str(x.id), value=x.name) for x in issue.locations if x.name
            ],
            number=issue.number,
            prices=[],
            publisher=Publisher(id=str(series.publisher.id), name=series.publisher.name)
            if series.publisher and series.publisher.name
            else None,
            reprints=[],
            series=Series(
                alternative_names=[],
                format=format_,
                id=str(series.id),
                name=series.name,
                start_year=series.start_year,
            ),
            store_date=issue.store_date,
            stories=[],
            summary=issue.summary,
            tags=[],
            teams=[Resource[str](id=str(x.id), value=x.name) for x in issue.teams if x.name],
            universes=[],
            urls=[Url(primary=True, value=str(issue.site_url))],
        )

    def _build_comic_info(
        self, series: Volume, issue: Issue, format_: Format | None = None
    ) -> ComicInfo:
        comic_info = ComicInfo(
            format=str(format_) if format_ else None,
            number=issue.number,
            pages=[],
            publisher=series.publisher.name if series.publisher else None,
            series=series.name,
            summary=issue.summary,
            title=issue.name,
            web=str(issue.site_url),
        )

        comic_info.cover_date = issue.cover_date
        comic_info.credits = {
            x.name: [r.strip() for r in re.split(r"[~\r\n,]+", x.roles) if r.strip()]
            for x in issue.creators
            if x.name
        }
        comic_info.character_list = [x.name for x in issue.characters if x.name]
        comic_info.team_list = [x.name for x in issue.teams if x.name]
        comic_info.location_list = [x.name for x in issue.locations if x.name]
        comic_info.story_arc_list = [x.name for x in issue.story_arcs if x.name]
        set_comic_info_note_id(comic_info, source=InformationSource.COMIC_VINE, value=issue.id)

        return comic_info

    def fetch(self, search: Search) -> MetadataResult | None:
        if not search.series.comicvine and search.issue.comicvine:
            try:
                temp = self.session.get_issue(issue_id=search.issue.comicvine)
                search.series.comicvine = temp.volume.id
            except ServiceError:
                pass

        series = self._fetch_series(search=search.series, filename=search.filename)
        if not series:
            return None

        issue = self._fetch_issue(
            series_id=series.id, search=search.issue, filename=search.filename
        )
        if not issue:
            return None
        format_: Format | None = None
        if self._override_format:
            format_ = prompt_select(
                message="Select a format", choices=[Choice(title=str(x), value=x) for x in Format]
            )

        return MetadataResult(
            comic_info=self._build_comic_info(series=series, issue=issue, format_=format_),
            metron_info=self._build_metron_info(series=series, issue=issue, format_=format_),
        )
