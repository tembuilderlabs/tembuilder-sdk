from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="RenderRequestParameters")


@_attrs_define
class RenderRequestParameters:
    """Input matching the version's `parameters_schema`. Parameters the
    version does not declare, at any depth, are ignored, as is `null`
    for an optional parameter. An optional parameter may be omitted.
    A required parameter that is missing or `null`, or any value of
    the wrong type, rejects the render with `400 COMMON_VALIDATION`
    and one `details` entry per offending value, for example
    `parameters.lines[0].qty: expected number, but got string`.

    """

    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        render_request_parameters = cls()

        render_request_parameters.additional_properties = d
        return render_request_parameters

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
