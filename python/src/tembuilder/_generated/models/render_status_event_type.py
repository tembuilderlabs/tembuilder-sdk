from typing import Literal

RenderStatusEventType = Literal["renders.status"]

RENDER_STATUS_EVENT_TYPE_VALUES: set[RenderStatusEventType] = {
    "renders.status",
}


def check_render_status_event_type(value: str) -> RenderStatusEventType:
    if value in RENDER_STATUS_EVENT_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {RENDER_STATUS_EVENT_TYPE_VALUES!r}")
