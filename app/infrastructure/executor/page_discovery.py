from app.domain.models.discovery import PageDiscoveryResult, DiscoveredElement


class PageDiscoveryClient:
    def __init__(self, executor_url: str = ""):
        from app.config import settings

        self._url = (executor_url or settings.executor_web_url).rstrip("/")

    async def discover(self) -> PageDiscoveryResult:
        import httpx

        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.post(f"{self._url}/agent/discover", timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return PageDiscoveryResult(
                title=data.get("title", ""),
                url=data.get("url", ""),
                elements=[DiscoveredElement(**e) for e in data.get("elements", [])],
                regions=data.get("regions", {}),
                screenshot=data.get("screenshot", ""),
            )
