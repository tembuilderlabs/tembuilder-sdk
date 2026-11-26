from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.project import Project


T = TypeVar("T", bound="Account")


@_attrs_define
class Account:
    """
    Attributes:
        api_key_id (UUID):
        workspace_id (UUID):
        project (Project):
        scopes (list[str]): Granted scopes, e.g. template:render, template:read.
    """

    api_key_id: UUID
    workspace_id: UUID
    project: Project
    scopes: list[str]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:

        api_key_id = str(self.api_key_id)

        workspace_id = str(self.workspace_id)

        project = self.project.to_dict()

        scopes = self.scopes

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "api_key_id": api_key_id,
                "workspace_id": workspace_id,
                "project": project,
                "scopes": scopes,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.project import Project  # noqa: PLC0415

        d = dict(src_dict)
        api_key_id = UUID(d.pop("api_key_id"))

        workspace_id = UUID(d.pop("workspace_id"))

        project = Project.from_dict(d.pop("project"))

        scopes = cast(list[str], d.pop("scopes"))

        account = cls(
            api_key_id=api_key_id,
            workspace_id=workspace_id,
            project=project,
            scopes=scopes,
        )

        account.additional_properties = d
        return account

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
