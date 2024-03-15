from __future__ import annotations

__all__ = [
    "list_files",
    "sanitize",
    "metron_to_metadata",
    "comic_to_metadata",
    "create_metadata",
    "metadata_to_metron",
    "metadata_to_comic",
]

import logging
import re
from datetime import date
from pathlib import Path

from natsort import humansorted, ns
from rich.prompt import Prompt

from perdoo import IMAGE_EXTENSIONS
from perdoo.archives import BaseArchive
from perdoo.console import CONSOLE, DatePrompt
from perdoo.models import ComicInfo, Metadata, MetronInfo

LOGGER = logging.getLogger(__name__)


def list_files(path: Path, *extensions: str) -> list[Path]:
    files = []
    for file in path.iterdir():
        if file.is_file():
            if not file.name.startswith(".") and (
                not extensions or file.suffix.lower() in extensions
            ):
                files.append(file)
        elif file.is_dir():
            files.extend(list_files(file, *extensions))
    return humansorted(files, alg=ns.NA | ns.G | ns.P)


def sanitize(value: str | None) -> str | None:
    if not value:
        return value
    value = re.sub(r"[^0-9a-zA-Z&! ]+", "", value.replace("-", " "))
    value = " ".join(value.split())
    return value.replace(" ", "-")


def metron_to_metadata(metron_info: MetronInfo) -> Metadata:
    LOGGER.info("Generating Metadata from MetronInfo details")
    from perdoo.models.metadata import (
        Credit,
        Format,
        Issue,
        Meta,
        Page,
        PageType,
        Resource,
        Series,
        Source,
        StoryArc,
        TitledResource,
        Tool,
    )

    try:
        source = Source.load(value=metron_info.id.source.value) if metron_info.id else None
    except ValueError as err:
        LOGGER.warning(err)
        source = None
    try:
        format_ = Format.load(value=metron_info.series.format_.value)
    except ValueError as err:
        LOGGER.warning(err)
        format_ = Format.COMIC

    pages = []
    for x in metron_info.pages:
        try:
            type_ = PageType.load(value=x.type_.value)
        except ValueError as err:
            LOGGER.warning(err)
            type_ = PageType.OTHER
        pages.append(
            Page(
                double_page=x.double_page,
                filename="",
                size=x.imageSize or 0,
                height=x.imageHeight or 0,
                width=x.imageWidth or 0,
                index=x.image,
                type_=type_,
            )
        )

    return Metadata(
        issue=Issue(
            characters=[
                TitledResource(
                    resources=[Resource(source=source, value=x.id)] if source and x.id else [],
                    title=x.value,
                )
                for x in metron_info.characters
            ],
            cover_date=metron_info.cover_date,
            credits=[
                Credit(
                    creator=TitledResource(
                        resources=[Resource(source=source, value=x.creator.id)]
                        if source and x.creator.id
                        else [],
                        title=x.creator.value,
                    ),
                    roles=[
                        TitledResource(
                            resources=[Resource(source=source, value=y.id)]
                            if source and y.id
                            else [],
                            title=y.value.value,
                        )
                        for y in x.roles
                    ],
                )
                for x in metron_info.credits
            ],
            format_=format_,
            language=metron_info.series.lang,
            locations=[
                TitledResource(
                    resources=[Resource(source=source, value=x.id)] if source and x.id else [],
                    title=x.value,
                )
                for x in metron_info.locations
            ],
            number=metron_info.number,
            page_count=metron_info.page_count,
            resources=[Resource(source=source, value=metron_info.id.value)] if source else [],
            series=Series(
                genres=[
                    TitledResource(
                        resources=[Resource(source=source, value=x.id)] if source and x.id else [],
                        title=x.value.value,
                    )
                    for x in metron_info.genres
                ],
                publisher=TitledResource(
                    resources=[Resource(source=source, value=metron_info.publisher.id)]
                    if source and metron_info.publisher.id
                    else [],
                    title=metron_info.publisher.value,
                ),
                resources=[Resource(source=source, value=metron_info.series.id)]
                if source and metron_info.series.id
                else [],
                title=metron_info.series.name,
                volume=metron_info.series.volume or 1,
            ),
            store_date=metron_info.store_date,
            story_arcs=[
                StoryArc(
                    number=x.number,
                    resources=[Resource(source=source, value=x.id)] if source and x.id else [],
                    title=x.name,
                )
                for x in metron_info.arcs
            ],
            summary=metron_info.summary,
            teams=[
                TitledResource(
                    resources=[Resource(source=source, value=x.id)] if source and x.id else [],
                    title=x.value,
                )
                for x in metron_info.teams
            ],
            title=metron_info.title,
        ),
        meta=Meta(date_=date.today(), tool=Tool(value="MetronInfo")),
        notes=metron_info.notes,
        pages=pages,
    )


def comic_to_metadata(comic_info: ComicInfo) -> Metadata:
    LOGGER.info("Generating Metadata from ComicInfo details")
    from perdoo.models.metadata import (
        Credit,
        Format,
        Issue,
        Meta,
        Page,
        PageType,
        Series,
        StoryArc,
        TitledResource,
        Tool,
    )

    try:
        format_ = Format.load(value=comic_info.format_) if comic_info.format_ else Format.COMIC
    except ValueError as err:
        LOGGER.warning(err)
        format_ = Format.COMIC

    pages = []
    for x in comic_info.pages:
        try:
            type_ = PageType.load(value=x.type_.value)
        except ValueError as err:
            LOGGER.warning(err)
            type_ = PageType.OTHER
        pages.append(
            Page(
                double_page=x.double_page,
                filename="",
                size=x.image_size or 0,
                height=x.image_height or 0,
                width=x.image_width or 0,
                index=x.image,
                type_=type_,
            )
        )

    return Metadata(
        issue=Issue(
            characters=[TitledResource(title=x) for x in comic_info.character_list],
            cover_date=comic_info.cover_date,
            credits=[
                Credit(
                    creator=TitledResource(title=creator),
                    roles=[TitledResource(title=x) for x in roles],
                )
                for creator, roles in comic_info.credits.items()
            ],
            format_=format_,
            language=comic_info.language_iso,
            locations=[TitledResource(title=x) for x in comic_info.location_list],
            number=comic_info.number or Prompt.ask("Issue number", console=CONSOLE),
            page_count=comic_info.page_count,
            series=Series(
                genres=[TitledResource(title=x) for x in comic_info.genre_list],
                publisher=TitledResource(
                    title=comic_info.publisher or Prompt.ask("Publisher title", console=CONSOLE)
                ),
                start_year=comic_info.volume
                if comic_info.volume and comic_info.volume >= 1900
                else None,
                title=comic_info.series or Prompt.ask("Series title", console=CONSOLE),
                volume=comic_info.volume if comic_info.volume and comic_info.volume < 1900 else 1,
            ),
            story_arcs=[StoryArc(title=x) for x in comic_info.story_arc_list],
            summary=comic_info.summary,
            teams=[TitledResource(title=x) for x in comic_info.team_list],
            title=comic_info.title,
        ),
        meta=Meta(date_=date.today(), tool=Tool(value="ComicInfo")),
        notes=comic_info.notes,
        pages=pages,
    )


def create_metadata(archive: BaseArchive) -> Metadata:
    LOGGER.info("Manually generating Metadata details")
    from perdoo.models.metadata import Issue, Meta, Series, TitledResource, Tool

    return Metadata(
        issue=Issue(
            series=Series(
                publisher=TitledResource(title=Prompt.ask("Publisher title", console=CONSOLE)),
                title=Prompt.ask("Series title", console=CONSOLE),
            ),
            number=Prompt.ask("Issue number", console=CONSOLE),
            page_count=len(
                [x for x in archive.list_filenames() if Path(x).suffix in IMAGE_EXTENSIONS]
            ),
        ),
        meta=Meta(date_=date.today(), tool=Tool(value="Manual")),
    )


def metadata_to_metron(metadata: Metadata) -> MetronInfo:
    LOGGER.info("Generating MetronInfo from Metadata details")
    from perdoo.models.metadata import Resource as MetadataResource, Source as MetadataSource
    from perdoo.models.metron_info import (
        Arc,
        Credit,
        Format,
        Genre,
        GenreResource,
        InformationSource,
        Page,
        PageType,
        Resource,
        Role,
        RoleResource,
        Series,
        Source,
    )

    def get_primary_source(
        resources: list[MetadataResource], resolution_order: list[MetadataSource]
    ) -> Resource | None:
        source_list = [x.source for x in resources]
        for entry in resolution_order:
            if entry in source_list:
                index = source_list.index(entry)
                return resources[index]
        return None

    primary_source = get_primary_source(
        resources=metadata.issue.resources,
        resolution_order=[
            MetadataSource.MARVEL,
            MetadataSource.METRON,
            MetadataSource.GRAND_COMICS_DATABASE,
            MetadataSource.COMICVINE,
            MetadataSource.LEAGUE_OF_COMIC_GEEKS,
        ],
    )

    try:
        format_ = Format.load(value=metadata.issue.format_.value)
    except ValueError as err:
        LOGGER.warning(err)
        format_ = None

    genres = []
    for genre in metadata.issue.series.genres:
        try:
            value = Genre.load(value=genre.title)
        except ValueError as err:
            LOGGER.warning(err)
            continue
        genres.append(
            GenreResource(
                id=next((x.value for x in genre.resources if x.source == primary_source), None),
                value=value,
            )
        )
    credits_ = []
    for credit in metadata.issue.credits:
        roles = []
        for role in credit.roles:
            try:
                value = Role.load(value=role.title)
            except ValueError as err:
                LOGGER.warning(err)
                value = Role.OTHER
            roles.append(
                RoleResource(
                    id=next((x.value for x in role.resources if x.source == primary_source), None),
                    value=value,
                )
            )
        credits_.append(
            Credit(
                creator=Resource(
                    id=next(
                        (x.value for x in credit.creator.resources if x.source == primary_source),
                        None,
                    ),
                    value=credit.creator.title,
                ),
                roles=roles,
            )
        )
    pages = []
    for page in metadata.pages:
        try:
            type_ = PageType.load(value=page.type_.value)
        except ValueError as err:
            LOGGER.warning(err)
            type_ = PageType.OTHER
        pages.append(
            Page(
                image=page.index,
                type_=type_,
                double_page=page.double_page,
                image_size=page.size,
                image_height=page.height,
                image_width=page.width,
            )
        )

    return MetronInfo(
        id=Source(
            source=InformationSource.load(value=primary_source.value),
            value=next(
                (x.value for x in metadata.issue.resources if x.source == primary_source), None
            ),
        )
        if primary_source
        else None,
        publisher=Resource(
            id=next(
                (
                    x.value
                    for x in metadata.issue.series.publisher.resources
                    if x.source == primary_source
                ),
                None,
            ),
            value=metadata.issue.series.publisher.title,
        ),
        series=Series(
            id=next(
                (x.value for x in metadata.issue.series.resources if x.source == primary_source),
                None,
            ),
            lang=metadata.issue.language,
            name=metadata.issue.series.title,
            sort_name=metadata.issue.series.title,
            volume=metadata.issue.series.volume,
            format_=format_,
        ),
        collection_title=metadata.issue.title,
        number=metadata.issue.number,
        summary=metadata.issue.summary,
        notes=metadata.notes,
        cover_date=metadata.issue.cover_date or DatePrompt.ask("Cover date", default=date.today()),
        store_date=metadata.issue.store_date,
        page_count=metadata.issue.page_count,
        genres=genres,
        arcs=[
            Arc(
                id=next((x.value for x in arc.resources if x.source == primary_source), None),
                name=arc.title,
                number=arc.number,
            )
            for arc in metadata.issue.story_arcs
        ],
        characters=[
            Resource(
                id=next((x.value for x in character.resources if x.source == primary_source), None),
                value=character.title,
            )
            for character in metadata.issue.characters
        ],
        teams=[
            Resource(
                id=next((x.value for x in team.resources if x.source == primary_source), None),
                value=team.title,
            )
            for team in metadata.issue.teams
        ],
        locations=[
            Resource(
                id=next((x.value for x in location.resources if x.source == primary_source), None),
                value=location.title,
            )
            for location in metadata.issue.locations
        ],
        credits=credits_,
        pages=pages,
    )


def metadata_to_comic(metadata: Metadata) -> ComicInfo:
    LOGGER.info("Generating ComicInfo from Metadata details")
    from perdoo.models.comic_info import Page, PageType

    pages = []
    for page in metadata.pages:
        try:
            type_ = PageType.load(value=page.type_.value)
        except ValueError as err:
            LOGGER.warning(err)
            type_ = PageType.OTHER
        pages.append(
            Page(
                image=page.index,
                type_=type_,
                double_page=page.double_page,
                image_size=page.size,
                image_height=page.height,
                image_width=page.width,
            )
        )

    output = ComicInfo(
        title=metadata.issue.title,
        series=metadata.issue.series.title,
        number=metadata.issue.number,
        volume=metadata.issue.series.volume,
        summary=metadata.issue.summary,
        notes=metadata.notes,
        publisher=metadata.issue.series.publisher.title,
        page_count=metadata.issue.page_count,
        language_iso=metadata.issue.language,
        format_=metadata.issue.format_.value,
        pages=pages,
    )
    output.cover_date = metadata.issue.cover_date or metadata.issue.store_date
    output.credits = {
        creator.title: [x.title for x in roles] for creator, roles in metadata.issue.credits
    }
    output.genre_list = [x.title for x in metadata.issue.series.genres]
    output.character_list = [x.title for x in metadata.issue.characters]
    output.team_list = [x.title for x in metadata.issue.teams]
    output.location_list = [x.title for x in metadata.issue.locations]
    output.story_arc_list = [x.title for x in metadata.issue.story_arcs]
    return output
