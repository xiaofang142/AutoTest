from app.interfaces.file_service import FileService
from app.lib.logger import get_logger

logger = get_logger(__name__)


class LocalFileService(FileService):
    async def upload(self, file_data: bytes, path: str) -> str:
        import aiofiles
        full_path = f"/tmp/autotest/{path}"
        import os
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(file_data)
        logger.info("File saved: %s", full_path)
        return full_path

    async def download(self, path: str) -> bytes:
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete(self, path: str) -> None:
        import os
        if os.path.exists(path):
            os.remove(path)
            logger.info("File deleted: %s", path)
