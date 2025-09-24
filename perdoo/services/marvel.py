__all__ = ["Marvel"]

import logging
from datetime import datetime

from esak.exceptions import ApiError
from esak.schemas.comic import Comic
from esak.schemas.series import Series
from esak.session import Session as Esak
from esak.sqlite_cache import SqliteCache
from natsort import humansorted, ns
from prompt_toolkit.styles import Style
from questionary import Choice, select
from requests.exceptions import ConnectionError, HTTPError  # noqa: A004
from rich.prompt import Confirm, Prompt

from perdoo import get_cache_root
from perdoo.console import CONSOLE
from perdoo.metadata import ComicInfo, MetronInfo
from perdoo.services._base import BaseService
from perdoo.settings import Marvel as MarvelSettings
from perdoo.utils import IssueSearch, Search, SeriesSearch

LOGGER = logging.getLogger(__name__)
DEFAULT_CHOICE = Choice(title="None of the Above", value=None)


class Marvel(BaseService[Series, Comic]):
    def __init__(self, settings: MarvelSettings):
        cache = SqliteCache(db_name=str(get_cache_root() / "esak.sqlite"), expire=14)
        self.session = Esak(
            public_key=settings.public_key, private_key=settings.private_key, cache=cache
        )

    def _search_series(self, name: str | None, volume: int | None, year: int | None) -> int | None:
        name = name or Prompt.ask("Series Name", console=CONSOLE)
        try:
            params = {"title": name}
            if year:
                params["startYear"] = year
            options = sorted(
                self.session.series_list(params=params), key=lambda x: (x.title, x.start_year)
            )
            if options:
                search = name
                if volume:
                    search += f" v{volume}"
                if year:
                    search += f" ({year})"
                choices = [
                    Choice(
                        title=[("class:dim", f"{x.id} | "), ("class:title", x.title)],
                        description=f"<Marvel Url>/series/{x.id}",
                        value=x,
                    )
                    for x in options
                ]
                choices.append(DEFAULT_CHOICE)
                selected = select(
                    f"Searching for Marvel Series '{search}'",
                    default=DEFAULT_CHOICE,
                    choices=choices,
                    style=Style([("dim", "dim")]),
                ).ask()
                if selected and selected != DEFAULT_CHOICE.title:
                    return selected.id
            else:
                LOGGER.warning(
                    "Unable to find any Series with the Title and StartYear: '%s %s'", name, year
                )
            if year:
                LOGGER.info("Searching again without the StartYear")
                return self._search_series(name=name, volume=volume, year=None)
            if Confirm.ask("Search Again", console=CONSOLE):
                return self._search_series(name=None, volume=None, year=None)
        except ConnectionError as err:
            LOGGER.error(err)
        except HTTPError as err:
            LOGGER.error(err)
        except ApiError as err:
            LOGGER.error(err)
        return None

    def fetch_series(self, search: SeriesSearch) -> Series | None:
        series_id = search.marvel or self._search_series(
            name=search.name, volume=search.volume, year=search.year
        )
        if not series_id:
            return None
        try:
            series = self.session.series(_id=series_id)
            search.marvel = series_id
            return series
        except ConnectionError as err:
            LOGGER.error(err)
            return None
        except HTTPError as err:
            LOGGER.error(err)
            return None
        except ApiError as err:
            LOGGER.error(err)
        if search.marvel:
            search.marvel = None
            return self.fetch_series(search=search)
        return None

    def _search_issue(self, series_id: int, number: str | None) -> int | None:
        try:
            options = humansorted(
                self.session.comics_list(
                    params={"noVariants": True, "series": series_id, "issueNumber": number}
                    if number
                    else {"noVariants": True, "series": series_id}
                ),
                key=lambda x: x.issue_number,
                alg=ns.NA | ns.G,
            )
            if options:
                choices = [
                    Choice(
                        title=[
                            ("class:dim", f"{x.id} | "),
                            ("class:title", f"{x.series.name} #{x.issue_number} - {x.format}"),
                        ],
                        description=f"<Marvel Url>/comics/{x.id}",
                        value=x,
                    )
                    for x in options
                ]
                choices.append(DEFAULT_CHOICE)
                selected = select(
                    f"Searching for Marvel Comic '#{number}'",
                    default=DEFAULT_CHOICE,
                    choices=choices,
                    style=Style([("dim", "dim")]),
                ).ask()
                if selected and selected != DEFAULT_CHOICE.title:
                    return selected.id
            else:
                LOGGER.warning(
                    "Unable to find any Comics with the Series and IssueNumber: '%s %s'",
                    series_id,
                    number,
                )
            if number:
                LOGGER.info("Searching again without the IssueNumber")
                return self._search_issue(series_id=series_id, number=None)
        except ConnectionError as err:
            LOGGER.error(err)
        except HTTPError as err:
            LOGGER.error(err)
        except ApiError as err:
            LOGGER.error(err)
        return None

    def fetch_issue(self, series_id: int, search: IssueSearch) -> Comic | None:
        issue_id = search.marvel or self._search_issue(series_id=series_id, number=search.number)
        if not issue_id:
            return None
        try:
            issue = self.session.comic(_id=issue_id)
            search.marvel = issue_id
            return issue
        except ConnectionError as err:
            LOGGER.error(err)
            return None
        except HTTPError as err:
            LOGGER.error(err)
            return None
        except ApiError as err:
            LOGGER.error(err)
        if search.marvel:
            search.marvel = None
            return self.fetch_issue(series_id=series_id, search=search)
        return None

    def _process_metron_info(self, series: Series, issue: Comic) -> MetronInfo | None:
        from perdoo.metadata.metron_info import (  # noqa: PLC0415
            GTIN,
            AgeRating,
            Arc,
            Credit,
            Format,
            Id,
            InformationSource,
            Price,
            Publisher,
            Resource,
            Role,
            Series,
            Url,
        )

        def load_format(value: str) -> Format:
            try:
                return Format.load(value=value.strip())
            except ValueError:
                return Format.SINGLE_ISSUE

        def load_age_rating(value: str) -> AgeRating:
            try:
                return AgeRating.load(value=value.strip())
            except ValueError:
                return AgeRating.UNKNOWN

        def load_role(value: str) -> Role:
            try:
                return Role.load(value=value.strip())
            except ValueError:
                return Role.OTHER

        return MetronInfo(
            ids=[Id(primary=True, source=InformationSource.MARVEL, value=str(issue.id))],
            publisher=Publisher(name="Marvel"),
            series=Series(
                id=str(series.id),
                name=series.title,
                format=load_format(value=issue.format),
                start_year=series.start_year,
            ),
            collection_title=issue.title,
            number=issue.issue_number,
            stories=[Resource[str](id=str(x.id), value=x.name) for x in issue.stories],
            summary=issue.description,
            prices=[Price(country="US", value=issue.prices.print)] if issue.prices else [],
            store_date=issue.dates.on_sale,
            page_count=issue.page_count,
            arcs=[Arc(id=str(x.id), name=x.name) for x in issue.events],
            characters=[Resource[str](id=str(x.id), value=x.name) for x in issue.characters],
            gtin=GTIN(isbn=issue.isbn, upc=issue.upc) if issue.isbn and issue.upc else None,
            age_rating=load_age_rating(value=series.rating),
            urls=[Url(primary=True, value=issue.urls.detail)],
            credits=[
                Credit(
                    creator=Resource[str](id=str(x.id), value=x.name),
                    roles=[Resource[Role](value=load_role(value=x.role))],
                )
                for x in issue.creators
            ],
            last_modified=datetime.now(),
        )

    def _process_comic_info(self, series: Series, issue: Comic) -> ComicInfo | None:
        from perdoo.metadata.comic_info import AgeRating  # noqa: PLC0415

        def load_age_rating(value: str) -> AgeRating:
            try:
                return AgeRating.load(value=value.strip())
            except ValueError:
                return AgeRating.UNKNOWN

        comic_info = ComicInfo(
            title=issue.title,
            series=series.title,
            number=issue.issue_number,
            summary=issue.description,
            publisher="Marvel",
            web=issue.urls.detail,
            page_count=issue.page_count,
            format=issue.format,
            age_rating=load_age_rating(value=series.rating),
        )

        comic_info.credits = {x.name: x.role.strip() for x in issue.creators}
        comic_info.character_list = [x.name for x in issue.characters]
        comic_info.story_arc_list = [x.name for x in issue.events]

        return comic_info

    def fetch(self, search: Search) -> tuple[MetronInfo | None, ComicInfo | None]:
        if not search.series.marvel and search.issue.marvel:
            try:
                temp = self.session.comic(_id=search.issue.marvel)
                search.series.marvel = temp.series.id
            except ApiError:
                pass

        series = self.fetch_series(search=search.series)
        if not series:
            return None, None

        issue = self.fetch_issue(series_id=series.id, search=search.issue)
        if not issue:
            return None, None

        metron_info = self._process_metron_info(series=series, issue=issue)
        comic_info = self._process_comic_info(series=series, issue=issue)

        return metron_info, comic_info
