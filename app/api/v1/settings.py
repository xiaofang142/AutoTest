"""LLM configuration and system settings API."""
from fastapi import APIRouter
from app.lib.logger import get_logger

router = APIRouter(tags=["settings"])
logger = get_logger(__name__)

# In-memory LLM config store
_llm_config = {
    "provider": "openai",
    "api_key": "",
    "api_base": "https://api.openai.com/v1",
    "extraction_model": "gpt-4o",
    "analysis_model": "gpt-4o-mini",
    "status": "disconnected",
}

_available_providers = {
    "openai": {"models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"], "base": "https://api.openai.com/v1"},
    "anthropic": {"models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"], "base": "https://api.anthropic.com"},
    "glm": {"models": ["glm-4", "glm-4v", "glm-3-turbo"], "base": "https://open.bigmodel.cn/api/paas/v4"},
    "custom": {"models": ["custom"], "base": ""},
}


@router.get("/settings/llm")
async def get_llm_config():
    return {"code": 0, "data": {k: v for k, v in _llm_config.items() if k != "api_key"}}


@router.put("/settings/llm")
async def update_llm_config(body: dict):
    global _llm_config
    for key in ["provider", "api_key", "api_base", "extraction_model", "analysis_model"]:
        if key in body:
            _llm_config[key] = body[key]
    # Update environment settings
    from app.config import settings
    if _llm_config.get("api_key"):
        settings.litellm_api_key = _llm_config["api_key"]
        _llm_config["status"] = "connected"
        # Reinitialize AI service
        from app.dependencies import init_services
        init_services()
    else:
        _llm_config["status"] = "disconnected"
    logger.info(f"LLM config updated: provider={_llm_config['provider']} model={_llm_config['extraction_model']}")
    return {"code": 0, "data": {k: v for k, v in _llm_config.items() if k != "api_key"}}


@router.get("/settings/llm/providers")
async def list_providers():
    return {"code": 0, "data": _available_providers}


@router.post("/settings/llm/test")
async def test_llm_connection():
    key = _llm_config.get("api_key", "")
    if not key:
        return {"code": 0, "data": {"status": "disconnected", "message": "未配置 API Key"}}
    try:
        import litellm
        resp = await litellm.acompletion(
            model=_llm_config["extraction_model"],
            api_key=key,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
        )
        return {"code": 0, "data": {"status": "connected", "message": f"连接成功: {resp.choices[0].message.content[:20]}..."}}
    except Exception as e:
        return {"code": 0, "data": {"status": "error", "message": str(e)}}
