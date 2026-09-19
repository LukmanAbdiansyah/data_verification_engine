from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
from dotenv import set_key

from ..database.engine import get_db
from ..models.models import SettingsMetadata
from ..schemas.schemas import SettingsSchema, TestConnectionResponse
from ..services.ai_client import AIClient

from dotenv import set_key, load_dotenv

router = APIRouter()

@router.get("/", response_model=SettingsSchema)
async def get_settings(db: AsyncSession = Depends(get_db)):
    load_dotenv(override=True)
    stmt = select(SettingsMetadata)
    rows = (await db.execute(stmt)).scalars().all()
    
    db_settings = {r.key: r.value for r in rows}
    
    return SettingsSchema(
        theme=db_settings.get('theme', 'system'),
        cache_enabled=db_settings.get('cache_enabled', 'true') == 'true',
        segy_validation_enabled=db_settings.get('segy_validation_enabled', 'true') == 'true',
        ai_enabled=db_settings.get('ai_enabled', 'true') == 'true',
        unsloth_base_url=os.getenv('UNSLOTH_BASE_URL', ''),
        api_key='*' * len(os.getenv('UNSLOTH_API_KEY', '')) if os.getenv('UNSLOTH_API_KEY') else '',
        model_name=os.getenv('UNSLOTH_MODEL', ''),
        timeout=int(os.getenv('AI_TIMEOUT', 120)),
        max_tokens=int(os.getenv('AI_MAX_TOKENS', 2500)),
        temperature=float(os.getenv('AI_TEMPERATURE', 0.0)),
        max_concurrent_requests=int(os.getenv('AI_MAX_CONCURRENT_REQUESTS', 2))
    )

@router.put("/")
async def update_settings(settings: SettingsSchema, db: AsyncSession = Depends(get_db)):
    keys = ['theme', 'cache_enabled', 'segy_validation_enabled', 'ai_enabled']
    
    for k in keys:
        val = str(getattr(settings, k)).lower()
        stmt = select(SettingsMetadata).where(SettingsMetadata.key == k)
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row:
            row.value = val
        else:
            db.add(SettingsMetadata(key=k, value=val))
            
    await db.commit()
    
    env_file = ".env"
    if not os.path.exists(env_file):
        open(env_file, 'a').close()
        
    set_key(env_file, 'UNSLOTH_BASE_URL', settings.unsloth_base_url)
    os.environ['UNSLOTH_BASE_URL'] = settings.unsloth_base_url
    
    if settings.api_key and not settings.api_key.startswith('***'):
        set_key(env_file, 'UNSLOTH_API_KEY', settings.api_key)
        os.environ['UNSLOTH_API_KEY'] = settings.api_key
        
    set_key(env_file, 'UNSLOTH_MODEL', settings.model_name)
    os.environ['UNSLOTH_MODEL'] = settings.model_name
    
    set_key(env_file, 'AI_TIMEOUT', str(settings.timeout))
    os.environ['AI_TIMEOUT'] = str(settings.timeout)
    
    set_key(env_file, 'AI_MAX_TOKENS', str(settings.max_tokens))
    os.environ['AI_MAX_TOKENS'] = str(settings.max_tokens)
    
    set_key(env_file, 'AI_TEMPERATURE', str(settings.temperature))
    os.environ['AI_TEMPERATURE'] = str(settings.temperature)
    
    set_key(env_file, 'AI_MAX_CONCURRENT_REQUESTS', str(settings.max_concurrent_requests))
    os.environ['AI_MAX_CONCURRENT_REQUESTS'] = str(settings.max_concurrent_requests)
    
    load_dotenv(override=True)
    return {"status": "success"}

@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_connection(settings: Optional[SettingsSchema] = None):
    base_url = (settings.unsloth_base_url if settings and settings.unsloth_base_url else os.getenv('UNSLOTH_BASE_URL', '')).strip()
    raw_key = settings.api_key if settings and settings.api_key else ''
    api_key = raw_key if raw_key and not raw_key.startswith('***') else os.getenv('UNSLOTH_API_KEY', '')
    model = (settings.model_name if settings and settings.model_name else os.getenv('UNSLOTH_MODEL', '')).strip()
    timeout = settings.timeout if settings and settings.timeout else 10

    if not base_url:
        return TestConnectionResponse(
            connected=False,
            model_ok=False,
            latency_ms=0.0,
            error="Base URL is empty. Please enter the Unsloth Base URL."
        )

    if not (base_url.startswith("http://") or base_url.startswith("https://")):
        return TestConnectionResponse(
            connected=False,
            model_ok=False,
            latency_ms=0.0,
            error=f"Invalid URL protocol: '{base_url}'. Must start with http:// or https://"
        )

    client = AIClient(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout=min(timeout, 30)
    )
    return await client.test_connection()
