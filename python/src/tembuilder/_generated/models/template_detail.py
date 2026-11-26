from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.template_input import TemplateInput
    from ..models.template_version import TemplateVersion


T = TypeVar("T", bound="TemplateDetail")


@_attrs_define
class TemplateDetail:
    """
    Attributes:
        id (UUID):
        slug (str):
        name (str):
        current_version (int): Version rendered when a request omits `version`.
        status (str): Status of the current version (`published` or `draft`).
        published_versions (list[int]): Every version that can be rendered, ascending.
        created_at (datetime.datetime | None):
        updated_at (datetime.datetime | None):
        versions (list[TemplateVersion]):
        input_ (TemplateInput): What one template version accepts at render time.
    """

    id: UUID
    slug: str
    name: str
    current_version: int
    status: str
    published_versions: list[int]
    created_at: datetime.datetime | None
    updated_at: datetime.datetime | None
    versions: list[TemplateVersion]
    input_: TemplateInput
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:

        id = str(self.id)

        slug = self.slug

        name = self.name

        current_version = self.current_version

        status = self.status

        published_versions = self.published_versions

        created_at: None | str
        if isinstance(self.created_at, datetime.datetime):
            created_at = self.created_at.isoformat()
        else:
            created_at = self.created_at

        updated_at: None | str
        if isinstance(self.updated_at, datetime.datetime):
            updated_at = self.updated_at.isoformat()
        else:
            updated_at = self.updated_at

        versions = []
        for versions_item_data in self.versions:
            versions_item = versions_item_data.to_dict()
            versions.append(versions_item)

        input_ = self.input_.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "slug": slug,
                "name": name,
                "current_version": current_version,
                "status": status,
                "published_versions": published_versions,
                "created_at": created_at,
                "updated_at": updated_at,
                "versions": versions,
                "input": input_,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.template_input import TemplateInput  # noqa: PLC0415
        from ..models.template_version import TemplateVersion  # noqa: PLC0415

        d = dict(src_dict)
        id = UUID(d.pop("id"))

        slug = d.pop("slug")

        name = d.pop("name")

        current_version = d.pop("current_version")

        status = d.pop("status")

        published_versions = cast(list[int], d.pop("published_versions"))

        def _parse_created_at(data: object) -> datetime.datetime | None:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                created_at_type_0 = datetime.datetime.fromisoformat(data)

                return created_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None, data)

        created_at = _parse_created_at(d.pop("created_at"))

        def _parse_updated_at(data: object) -> datetime.datetime | None:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                updated_at_type_0 = datetime.datetime.fromisoformat(data)

                return updated_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None, data)

        updated_at = _parse_updated_at(d.pop("updated_at"))

        versions = []
        _versions = d.pop("versions")
        for versions_item_data in _versions:
            versions_item = TemplateVersion.from_dict(versions_item_data)

            versions.append(versions_item)

        input_ = TemplateInput.from_dict(d.pop("input"))

        template_detail = cls(
            id=id,
            slug=slug,
            name=name,
            current_version=current_version,
            status=status,
            published_versions=published_versions,
            created_at=created_at,
            updated_at=updated_at,
            versions=versions,
            input_=input_,
        )

        template_detail.additional_properties = d
        return template_detail

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
