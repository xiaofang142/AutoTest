from abc import ABC, abstractmethod


class FileService(ABC):
    @abstractmethod
    async def upload(self, file_data: bytes, path: str) -> str:
        ...

    @abstractmethod
    async def download(self, path: str) -> bytes:
        ...

    @abstractmethod
    async def delete(self, path: str) -> None:
        ...
