from dataclasses import dataclass

from configs import base


@dataclass(frozen=True)
class SourceProfile:
    source: str
    source_vendor: str
    source_surface: str
    source_capture_method: str
    source_skill: str
    allowed_symbols: tuple[str, ...]


_PROFILES: dict[str, SourceProfile] = {
    base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE: SourceProfile(
        source=base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE,
        source_vendor=base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE_VENDOR,
        source_surface=base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE_SURFACE,
        source_capture_method=base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE_CAPTURE_METHOD,
        source_skill=base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE_SKILL,
        allowed_symbols=base.EXTERNAL_SIGNAL_STAGE1_1_ALLOWED_SYMBOLS,
    ),
}


def get_source_profile(source: str) -> SourceProfile:
    """Return the registered SourceProfile for the given source id.

    Raises KeyError if the source is not registered.
    """
    if source not in _PROFILES:
        raise KeyError(f"No source profile registered for source: {source!r}")
    return _PROFILES[source]
