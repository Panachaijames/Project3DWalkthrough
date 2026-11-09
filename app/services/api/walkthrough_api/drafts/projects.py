"""createProject and listOffices (docs/upload/DESIGN.md U-13.3, U-8.4).

createProject writes meta.json (sourceKind 'cad', latestVersion 0) through Store.create_project and project-settings.json
(office; naming derived from the names, naming.py); `newOfficeName` creates that office's empty memory
(data/mappings/<officeId>.json; an office of that id that exists already is used as it is). Refused: a name, short name
or project number that cannot be used, an unknown office and a wanted id that is not 2 - 40 characters of the pattern
(422 bad_project); an id that is taken or reserved (409 project_exists, `details.suggested` = the next free id).
"""
from __future__ import annotations

import unicodedata

from ..errors import ApiError
from ..jsonio import iso_utc
from ..models import ProjectDetail
from ..models_upload import NewProjectRequest, OfficeInfo, OfficeList, OfficeMapping
from ..store.base import NewProject, NotFound, Naming, ProjectSettingsFile, Store, StoreConflict
from .. import views
from . import naming

MAX_NAME = 200
MAX_SHORT_NAME = 100
MAX_PROJECT_NO = 64


def has_control(text: str) -> bool:
    return any(unicodedata.category(c) in ('Cc', 'Cf', 'Cs') and c not in '‍‌' for c in text)


def _text(value: str | None, what: str, limit: int, required: bool) -> str | None:
    text = (value or '').strip()
    if not text:
        if required:
            raise ApiError(422, 'bad_project', f'the project needs a {what}')
        return None
    if len(text) > limit:
        raise ApiError(422, 'bad_project', f'the {what} is {len(text)} characters; at most {limit} are taken')
    if has_control(text):
        raise ApiError(422, 'bad_project', f'the {what} holds a control character')
    return text


def _exists(store: Store, project_id: str) -> bool:
    try:
        store.get_project(project_id)
    except NotFound:
        return False
    return True


def create_project(store: Store, body: NewProjectRequest) -> ProjectDetail:
    name = _text(body.name, 'name', MAX_NAME, required=True)
    assert name is not None
    short_name = _text(body.short_name, 'short name', MAX_SHORT_NAME, required=False) or name[:MAX_SHORT_NAME]
    project_no = _text(body.project_no, 'project number', MAX_PROJECT_NO, required=False)
    office_name: str | None = None
    office = body.office or None
    if office is not None:
        if store.get_office(office) is None:
            raise ApiError(422, 'bad_project', f'there is no office {office!r}: pick a known office or a new one')
    elif body.new_office_name is not None and body.new_office_name.strip():
        office_name = _text(body.new_office_name, 'office name', MAX_NAME, required=True)
        assert office_name is not None
        office = naming.office_id(office_name)

    if body.id is not None and body.id != '':
        project_id = body.id                                  # as given: ' new' (or one with a newline) is refused
        problem = naming.id_problem(project_id)
        if problem:
            raise ApiError(422, 'bad_project', problem)
    else:
        project_id = naming.derived_project_id(name)
    if project_id in naming.RESERVED_IDS or _exists(store, project_id):
        suggested = naming.next_free(project_id, lambda i: _exists(store, i))
        why = 'is reserved' if project_id in naming.RESERVED_IDS else 'is taken'
        raise ApiError(409, 'project_exists', f'the project id {project_id} {why}: {suggested} is free',
                       {'suggested': suggested})
    store.check_path(store.deepest_run_path(project_id))            # PathTooLong: the data folder is too deep

    try:
        meta = store.create_project(NewProject(id=project_id, name=name, short_name=short_name, project_no=project_no,
                                               source_kind='cad'))
    except StoreConflict:
        suggested = naming.next_free(project_id, lambda i: _exists(store, i))
        raise ApiError(409, 'project_exists', f'the project id {project_id} is taken: {suggested} is free',
                       {'suggested': suggested}) from None
    now = iso_utc()
    if office_name is not None and office is not None and store.get_office(office) is None:
        store.write_office(OfficeMapping(format='office-mapping/1', id=office, name=office_name, created_at=now,
                                         updated_at=now, layers={}, furniture_words={}))
    derived = naming.naming(name, short_name)
    store.write_project_settings(project_id, ProjectSettingsFile(
        office=office, naming=Naming(photo_name=derived['photoName'], max_prefix=derived['maxPrefix'],
                                     max_file_name=derived['maxFileName']),
        offset=None, updated_at=now))
    return views.project_detail(store, meta)


def list_offices(store: Store) -> OfficeList:
    offices = sorted(store.list_offices(), key=lambda m: (m.name.casefold(), m.id))
    return OfficeList(offices=[OfficeInfo(id=m.id, name=m.name, layers=len(m.layers), updated_at=m.updated_at)
                               for m in offices])
