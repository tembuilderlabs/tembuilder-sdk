from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.template_input_example_parameters import TemplateInputExampleParameters
    from ..models.template_input_parameters_item import TemplateInputParametersItem
    from ..models.template_input_parameters_schema import TemplateInputParametersSchema
    from ..models.template_variant import TemplateVariant


T = TypeVar("T", bound="TemplateInput")


@_attrs_define
class TemplateInput:
    """What one template version accepts at render time.

    Attributes:
        version (int):
        variants (list[TemplateVariant]):
        parameters (list[TemplateInputParametersItem]): Parameter definitions exactly as declared in the template (name,
            type, required, default, fields, itemSchema).
        parameters_schema (TemplateInputParametersSchema): JSON Schema (2020-12) describing the `parameters` object of a
            render request.
        example_parameters (TemplateInputExampleParameters): A valid starting value built from defaults, ready to edit.
    """

    version: int
    variants: list[TemplateVariant]
    parameters: list[TemplateInputParametersItem]
    parameters_schema: TemplateInputParametersSchema
    example_parameters: TemplateInputExampleParameters
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:

        version = self.version

        variants = []
        for variants_item_data in self.variants:
            variants_item = variants_item_data.to_dict()
            variants.append(variants_item)

        parameters = []
        for parameters_item_data in self.parameters:
            parameters_item = parameters_item_data.to_dict()
            parameters.append(parameters_item)

        parameters_schema = self.parameters_schema.to_dict()

        example_parameters = self.example_parameters.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "version": version,
                "variants": variants,
                "parameters": parameters,
                "parameters_schema": parameters_schema,
                "example_parameters": example_parameters,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.template_input_example_parameters import TemplateInputExampleParameters  # noqa: PLC0415
        from ..models.template_input_parameters_item import TemplateInputParametersItem  # noqa: PLC0415
        from ..models.template_input_parameters_schema import TemplateInputParametersSchema  # noqa: PLC0415
        from ..models.template_variant import TemplateVariant  # noqa: PLC0415

        d = dict(src_dict)
        version = d.pop("version")

        variants = []
        _variants = d.pop("variants")
        for variants_item_data in _variants:
            variants_item = TemplateVariant.from_dict(variants_item_data)

            variants.append(variants_item)

        parameters = []
        _parameters = d.pop("parameters")
        for parameters_item_data in _parameters:
            parameters_item = TemplateInputParametersItem.from_dict(parameters_item_data)

            parameters.append(parameters_item)

        parameters_schema = TemplateInputParametersSchema.from_dict(d.pop("parameters_schema"))

        example_parameters = TemplateInputExampleParameters.from_dict(d.pop("example_parameters"))

        template_input = cls(
            version=version,
            variants=variants,
            parameters=parameters,
            parameters_schema=parameters_schema,
            example_parameters=example_parameters,
        )

        template_input.additional_properties = d
        return template_input

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
