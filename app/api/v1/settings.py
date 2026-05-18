"""LLM configuration - minimal: API Key, Base URL, Model name."""
import json
from pathlib import Path

from fastapi import APIRouter

from app.config import settings as env_settings
from app.lib.logger import get_logger

router = APIRouter(tags=["settings"])
logger = get_logger(__name__)

_CONFIG_FILE = Path(__file__).resolve().parent.parent.parent.parent / ".llm_config.json"
_llm_config = None


def _get_config():
    global _llm_config
    if _llm_config is None:
        _llm_config = {
            "api_key": env_settings.litellm_api_key or "",
            "api_base": env_settings.litellm_api_base or "https://api.deepseek.com",
            "extraction_model": env_settings.extraction_model or "deepseek-v4-flash",
            "analysis_model": env_settings.analysis_model or "deepseek-v4-flash",
            "status": "connected" if env_settings.litellm_api_key else "disconnected",
        }
        if _CONFIG_FILE.exists():
            try:
                saved = json.loads(_CONFIG_FILE.read_text())
                _llm_config.update(saved)
                if _llm_config.get("api_key"):
                    _llm_config["status"] = "connected"
                    env_settings.litellm_api_key = _llm_config["api_key"]
            except (json.JSONDecodeError, OSError):
                pass
    return _llm_config


def _rebuild_ai_service():
    from app.dependencies import init_services
    init_services()


@router.get("/settings/llm")
async def get_llm_config():
    cfg = _get_config()
    return {"code": 0, "data": dict(cfg)}


@router.put("/settings/llm")
async def update_llm_config(body: dict):
    cfg = _get_config()
    for key in ("api_key", "api_base", "extraction_model", "analysis_model"):
        if key in body and body[key] is not None:
            cfg[key] = body[key]

    if cfg.get("api_key"):
        cfg["status"] = "connected"
        env_settings.litellm_api_key = cfg["api_key"]
        env_settings.extraction_model = cfg.get("extraction_model", "deepseek-v4-flash")
        env_settings.analysis_model = cfg.get("analysis_model", "deepseek-v4-flash")
        env_settings.litellm_api_base = cfg.get("api_base", "")
    else:
        cfg["status"] = "disconnected"

    _rebuild_ai_service()
    logger.info("LLM config updated")

    try:
        persist = {k: v for k, v in cfg.items() if k != "status"}
        _CONFIG_FILE.write_text(json.dumps(persist, ensure_ascii=False, indent=2))
    except OSError as e:
        logger.warning("Failed to persist config: %s", e)

    return {"code": 0, "data": dict(cfg)}


@router.post("/settings/llm/test")
async def test_llm_connection():
    cfg = _get_config()
    key = cfg.get("api_key", "")
    if not key:
        return {"code": 0, "data": {"status": "disconnected", "message": "未配置 API Key"}}
    try:
        import litellm
        model = cfg["extraction_model"]
        api_base = cfg.get("api_base", "")
        # OpenAI-compatible APIs need openai/ prefix for LiteLLM
        if api_base and "/" not in model:
            model = f"openai/{model}"
        resp = await litellm.acompletion(
            model=model, api_key=key, api_base=api_base or None,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
        )
        reply = resp.choices[0].message.content[:30]
        cfg["status"] = "connected"
        return {"code": 0, "data": {"status": "connected", "message": f"✅ 连接成功: {reply}"}}
    except Exception as e:
        cfg["status"] = "error"
        return {"code": 0, "data": {"status": "error", "message": f"❌ 连接失败: {e}"}}
