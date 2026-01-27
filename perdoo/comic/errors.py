__all__ = ["ComicArchiveError", "ComicError", "ComicMetadataError"]


class ComicError(Exception): ...


class ComicArchiveError(ComicError): ...


class ComicMetadataError(ComicError): ...
