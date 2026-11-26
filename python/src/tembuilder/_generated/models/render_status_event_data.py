from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.render_status_event_data_error import RenderStatusEventDataError
    from ..models.render_status_event_data_links import RenderStatusEventDataLinks
    from ..models.render_status_event_data_output import RenderStatusEventDataOutput


T = TypeVar("T", bound="RenderStatusEventData")


@_attrs_define
class RenderStatusEventData:
    """
    Attributes:
        render_id (UUID):
        workspace_id (UUID):
        project_id (UUID):
        template_id (UUID):
        template_version (int):
        status (str):
        started_at (datetime.datetime):
        completed_at (datetime.datetime):
        duration_ms (int):
        links (RenderStatusEventDataLinks):
        variant (str | Unset):
        error (RenderStatusEventDataError | Unset):
        output (RenderStatusEventDataOutput | Unset):
    """

    render_id: UUID
    workspace_id: UUID
    project_id: UUID
    template_id: UUID
    template_version: int
    status: str
    started_at: datetime.datetime
    completed_at: datetime.datetime
    duration_ms: int
    links: RenderStatusEventDataLinks
    variant: str | Unset = UNSET
    error: RenderStatusEventDataError | Unset = UNSET
    output: RenderStatusEventDataOutput | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:

        render_id = str(self.render_id)

        workspace_id = str(self.workspace_id)

        project_id = str(self.project_id)

        template_id = str(self.template_id)

        template_version = self.template_version

        status = self.status

        started_at = self.started_at.isoformat()

        completed_at = self.completed_at.isoformat()

        duration_ms = self.duration_ms

        links = self.links.to_dict()

        variant = self.variant

        error: dict[str, Any] | Unset = UNSET
        if not isinstance(self.error, Unset):
            error = self.error.to_dict()

        output: dict[str, Any] | Unset = UNSET
        if not isinstance(self.output, Unset):
            output = self.output.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "render_id": render_id,
                "workspace_id": workspace_id,
                "project_id": project_id,
                "template_id": template_id,
                "template_version": template_version,
                "status": status,
                "started_at": started_at,
                "completed_at": completed_at,
                "duration_ms": duration_ms,
                "links": links,
            }
        )
        if variant is not UNSET:
            field_dict["variant"] = variant
        if error is not UNSET:
            field_dict["error"] = error
        if output is not UNSET:
            field_dict["output"] = output

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.render_status_event_data_error import RenderStatusEventDataError  # noqa: PLC0415
        from ..models.render_status_event_data_links import RenderStatusEventDataLinks  # noqa: PLC0415
        from ..models.render_status_event_data_output import RenderStatusEventDataOutput  # noqa: PLC0415

        d = dict(src_dict)
        render_id = UUID(d.pop("render_id"))

        workspace_id = UUID(d.pop("workspace_id"))

        project_id = UUID(d.pop("project_id"))

        template_id = UUID(d.pop("template_id"))

        template_version = d.pop("template_version")

        status = d.pop("status")

        started_at = datetime.datetime.fromisoformat(d.pop("started_at"))

        completed_at = datetime.datetime.fromisoformat(d.pop("completed_at"))

        duration_ms = d.pop("duration_ms")

        links = RenderStatusEventDataLinks.from_dict(d.pop("links"))

        variant = d.pop("variant", UNSET)

        _error = d.pop("error", UNSET)
        error: RenderStatusEventDataError | Unset
        if isinstance(_error, Unset):
            error = UNSET
        else:
            error = RenderStatusEventDataError.from_dict(_error)

        _output = d.pop("output", UNSET)
        output: RenderStatusEventDataOutput | Unset
        if isinstance(_output, Unset):
            output = UNSET
        else:
            output = RenderStatusEventDataOutput.from_dict(_output)

        render_status_event_data = cls(
            render_id=render_id,
            workspace_id=workspace_id,
            project_id=project_id,
            template_id=template_id,
            template_version=template_version,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            links=links,
            variant=variant,
            error=error,
            output=output,
        )

        render_status_event_data.additional_properties = d
        return render_status_event_data

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
