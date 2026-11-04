"""The seed table of DESIGN.md 9.2: which prototype files make which project version. Paths are relative to the
prototype (project) folder, POSIX style; the seed only reads them (never writes there, never imports prototype code).

| project / v            | from                                             | model     | stages    |
|------------------------|--------------------------------------------------|-----------|-----------|
| bank-sampeng / 1       | bank_test/previous_before_fix_round_2026-10-27/  | copied    | copied    |
| bank-sampeng / 2       | bank_test/                                       | copied    | copied    |
| presidential-suite / 1 | presidential_test/                               | converted | converted |
| sukhumvit-house / 1    | cad_test/                                        | converted | converted |
| hotel-lobby / 1        | hotel_test/                                      | copied    | none      |
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ModelHow = Literal['copy', 'suite', 'house']
StagesHow = Literal['copy', 'suite', 'house']
PresentationHow = Literal['bank', 'suite', 'house', 'hotel']


@dataclass(frozen=True)
class Asset:
    src: str                      # relative to the prototype folder
    name: str                     # file name under versions/<n>/assets/
    role: Literal['plan-picture', 'thumbnail']
    floor: str | None = None
    model_ref: str | None = None  # plan pictures: model.pictureFrame[floor].file


@dataclass(frozen=True)
class VersionSource:
    project_id: str
    version: int
    label: str
    source_kind: Literal['cad', 'pictures']
    folder: str                   # the version's prototype folder ("from")
    model: ModelHow
    model_files: tuple[str, ...]  # what the model is made of (relative to `folder`); createdAt is the newest's mtime
    stages: StagesHow | None
    stages_file: str | None
    presentation: PresentationHow
    assets: tuple[Asset, ...]
    downloads: tuple[str, ...]    # copied byte for byte into downloads/ (relative to `folder`)
    source: tuple[str, ...]       # copied byte for byte into source/ (relative to `folder`)
    max_script: str | None        # the .ms among the downloads
    stamp_source: str = 'model.json'   # relative to the version folder
    extra_reads: tuple[str, ...] = field(default=())   # other files the converters read (relative to `folder`)

    def path(self, rel: str) -> str:
        """A file of this version relative to the prototype folder."""
        return f'{self.folder}/{rel}' if self.folder else rel


BANK_V1 = 'bank_test/previous_before_fix_round_2026-10-27'

SEED_TABLE: tuple[VersionSource, ...] = (
    VersionSource(
        project_id='bank-sampeng', version=1,
        label='27 Oct 2026: two levels, openings from the detector (before the fix round)',
        source_kind='cad', folder=BANK_V1,
        model='copy', model_files=('src/bank_model.json',),
        stages='copy', stages_file='src/bank_stages.json', presentation='bank',
        assets=(Asset('bank_topview.png', 'topview.png', 'thumbnail'),),
        downloads=('Bangkok_Bank_Sampeng.ms',), max_script='Bangkok_Bank_Sampeng.ms',
        source=('src/bank_summary.json', 'README.md'),
    ),
    VersionSource(
        project_id='bank-sampeng', version=2, label='29 Oct 2026: furniture boxes',
        source_kind='cad', folder='bank_test',
        model='copy', model_files=('src/bank_model.json',),
        stages='copy', stages_file='src/bank_stages.json', presentation='bank',
        assets=(Asset('bank_topview.png', 'topview.png', 'thumbnail'),),
        downloads=('Bangkok_Bank_Sampeng.ms', 'bank_furniture_list.csv'), max_script='Bangkok_Bank_Sampeng.ms',
        source=('src/bank_project.json', 'src/bank_summary.json', 'README.md'),
    ),
    VersionSource(
        project_id='presidential-suite', version=1, label='29 Oct 2026: furniture boxes',
        source_kind='cad', folder='presidential_test',
        model='suite', model_files=('src/pres2_model.json',),
        stages='suite', stages_file='src/pres2_stages.json', presentation='suite',
        assets=(Asset('presidential_topview.png', 'topview.png', 'thumbnail'),),
        downloads=('Presidential_Suite.ms', 'presidential_furniture_list.csv'), max_script='Presidential_Suite.ms',
        source=('src/pres2_model.json', 'src/pres2_stages.json', 'src/furniture.json', 'src/floor_spec.json', 'README.md'),
        stamp_source='source/pres2_model.json',   # the .ms was made from pres2_model.json (DESIGN.md 6.3, 18.6)
    ),
    VersionSource(
        project_id='sukhumvit-house', version=1, label='29 Oct 2026: openings and furniture boxes',
        source_kind='cad', folder='cad_test',
        model='house', model_files=('src/house3d_merged.json', 'src/furniture_house.json'),
        stages='house', stages_file='src/house3d_stages.json', presentation='house',
        assets=(),                                 # no top view: the card shows a placeholder (DESIGN.md 18.28)
        downloads=('house_furniture_list.csv',), max_script=None,
        source=('src/house3d_merged.json', 'src/furniture_house.json', 'src/house3d_stages.json', 'src/heights.json',
                'src/openings.json', 'OPENINGS_CHANGES.md'),
    ),
    VersionSource(
        project_id='hotel-lobby', version=1,
        label='2 Nov 2026: read from two plan pictures',
        source_kind='pictures', folder='hotel_test',
        model='copy', model_files=('src/hotel_model.json',),    # floor 2's furniture stays as drawn (the owner, 3 Nov)
        stages=None, stages_file=None, presentation='hotel',
        assets=(Asset('source/floor1_plan.png', 'floor1_plan.png', 'plan-picture', 'F1', '../source/floor1_plan.png'),
                Asset('source/floor2_plan.png', 'floor2_plan.png', 'plan-picture', 'F2', '../source/floor2_plan.png'),
                Asset('hotel_topview.png', 'topview.png', 'thumbnail')),
        downloads=('Hotel_Lobby.ms', 'hotel_furniture_list.csv'), max_script='Hotel_Lobby.ms',
        source=('src/hotel_project.json', 'src/hotel_summary.json', 'src/picture_readings.json', 'src/takeoff.json',
                'README.md'),
    ),
)

PROJECT_SOURCE_KIND = {v.project_id: v.source_kind for v in SEED_TABLE}


def reads(v: VersionSource) -> list[str]:
    """Every prototype file the seed reads for a version (relative to the prototype folder), in a stable order."""
    rels = [*v.model_files, *((v.stages_file,) if v.stages_file else ()), *v.extra_reads,
            *(a.src for a in v.assets), *v.downloads, *v.source]
    out: list[str] = []
    for rel in rels:
        p = v.path(rel)
        if p not in out:
            out.append(p)
    return out
