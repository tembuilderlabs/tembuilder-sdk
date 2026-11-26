from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.render_request_parameters import RenderRequestParameters


T = TypeVar("T", bound="RenderRequest")


@_attrs_define
class RenderRequest:
    """
    Attributes:
        template_id (UUID): Template UUID (slugs are not accepted here).
        version (int | Unset): Published version to render. Defaults to the template's current version.
        variant (str | Unset): Variant name. Defaults to the base variant.
        parameters (RenderRequestParameters | Unset): Input matching the version's `parameters_schema`.
    """

    template_id: UUID
    version: int | Unset = UNSET
    variant: str | Unset = UNSET
    parameters: RenderRequestParameters | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:

        template_id = str(self.template_id)

        version = self.version

        variant = self.variant

        parameters: dict[str, Any] | Unset = UNSET
        if not isinstance(self.parameters, Unset):
            parameters = self.parameters.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "template_id": template_id,
            }
        )
        if version is not UNSET:
            field_dict["version"] = version
        if variant is not UNSET:
            field_dict["variant"] = variant
        if parameters is not UNSET:
            field_dict["parameters"] = parameters

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.render_request_parameters import RenderRequestParameters  # noqa: PLC0415

        d = dict(src_dict)
        template_id = UUID(d.pop("template_id"))

        version = d.pop("version", UNSET)

        variant = d.pop("variant", UNSET)

        _parameters = d.pop("parameters", UNSET)
        parameters: RenderRequestParameters | Unset
        if isinstance(_parameters, Unset):
            parameters = UNSET
        else:
            parameters = RenderRequestParameters.from_dict(_parameters)

        render_request = cls(
            template_id=template_id,
            version=version,
            variant=variant,
            parameters=parameters,
        )

        render_request.additional_properties = d
        return render_request

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
