from pydantic import BaseModel


class DiscoveredElement(BaseModel):
    type: str
    text: str
    selector_hint: str = ""
    is_visible: bool = True
    region: str = "unknown"


class PageDiscoveryResult(BaseModel):
    title: str = ""
    url: str = ""
    elements: list[DiscoveredElement] = []
    regions: dict[str, int] = {}
    screenshot: str = ""
