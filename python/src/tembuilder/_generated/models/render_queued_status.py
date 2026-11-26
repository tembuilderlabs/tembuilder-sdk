from typing import Literal

RenderQueuedStatus = Literal["queued"]

RENDER_QUEUED_STATUS_VALUES: set[RenderQueuedStatus] = {
    "queued",
}


def check_render_queued_status(value: str) -> RenderQueuedStatus:
    if value in RENDER_QUEUED_STATUS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {RENDER_QUEUED_STATUS_VALUES!r}")
