import httpx
import asyncio
import json
import time
import logging
import re
from typing import Dict, List, Any, Optional
from ..schemas.schemas import AIResponseSchema, TestConnectionResponse

logger = logging.getLogger(__name__)

class AIClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 120, max_tokens: int = 2500, temperature: float = 0, max_concurrent: int = 2):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_tokens = max(max_tokens, 2000)
        self.temperature = temperature
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def _build_url(self) -> str:
        base = self.base_url
        if base.endswith('/v1'):
            return f"{base}/chat/completions"
        elif '/v1' in base:
            return f"{base}/chat/completions"
        else:
            return f"{base}/v1/chat/completions"

    def _build_models_url(self) -> str:
        base = self.base_url
        if base.endswith('/v1'):
            return f"{base}/models"
        elif '/v1' in base:
            return f"{base}/models"
        else:
            return f"{base}/v1/models"
    
    def _headers(self) -> Dict[str, str]:
        h = {'Content-Type': 'application/json'}
        if self.api_key:
            h['Authorization'] = f'Bearer {self.api_key}'
        return h
    
    async def chat_completion(self, messages: List[Dict[str, str]], cache_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]
        
        url = self._build_url()
        payload = {
            'model': self.model,
            'messages': messages,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
        }
        
        async with self._semaphore:
            for attempt in range(3):
                try:
                    start = time.time()
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(url, json=payload, headers=self._headers())
                    latency = int((time.time() - start) * 1000)
                    response.raise_for_status()
                    data = response.json()
                    msg_obj = data['choices'][0]['message']
                    content = msg_obj.get('content') or ''
                    reasoning_content = msg_obj.get('reasoning_content') or ''
                    
                    # Search for JSON in content first, then in reasoning_content
                    text_sources = [content]
                    if reasoning_content:
                        text_sources.append(reasoning_content)
                    
                    parsed_result = None
                    for text in text_sources:
                        if not text.strip():
                            continue
                        try:
                            parsed = json.loads(text)
                            validated = AIResponseSchema(**parsed)
                            parsed_result = validated.model_dump()
                            break
                        except Exception:
                            json_match = re.search(r'\{[\s\S]*\}', text)
                            if json_match:
                                try:
                                    parsed = json.loads(json_match.group())
                                    validated = AIResponseSchema(**parsed)
                                    parsed_result = validated.model_dump()
                                    break
                                except Exception:
                                    pass
                    
                    if parsed_result:
                        parsed_result['latency_ms'] = latency
                        if cache_key:
                            self._cache[cache_key] = parsed_result
                        return parsed_result
                        
                    if attempt < 2:
                        logger.warning(f'AI response parse failed, retrying (attempt {attempt+1})')
                        continue
                    logger.error(f'AI response invalid after retries: content={content[:200]} reasoning={reasoning_content[:200]}')
                    return None
                except httpx.TimeoutException:
                    logger.warning(f'AI request timeout (attempt {attempt+1})')
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return None
                except httpx.HTTPStatusError as e:
                    logger.error(f'AI HTTP error: {e.response.status_code}')
                    return None
                except Exception as e:
                    logger.error(f'AI request error: {type(e).__name__}')
                    if attempt < 2:
                        await asyncio.sleep(1)
                        continue
                    return None
        return None
    
    async def chat_completion_json(self, messages: List[Dict[str, str]], cache_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """General chat completion returning arbitrary parsed JSON dict."""
        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]
        
        url = self._build_url()
        payload = {
            'model': self.model,
            'messages': messages,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
        }
        
        async with self._semaphore:
            for attempt in range(3):
                try:
                    start = time.time()
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(url, json=payload, headers=self._headers())
                    latency = int((time.time() - start) * 1000)
                    response.raise_for_status()
                    data = response.json()
                    msg_obj = data['choices'][0]['message']
                    content = msg_obj.get('content') or ''
                    reasoning_content = msg_obj.get('reasoning_content') or ''
                    
                    text_sources = [content]
                    if reasoning_content:
                        text_sources.append(reasoning_content)
                    
                    for text in text_sources:
                        if not text.strip():
                            continue
                        # Strip markdown formatting
                        clean_text = text.strip()
                        if clean_text.startswith('```'):
                            clean_text = re.sub(r'^```(?:json)?\s*', '', clean_text)
                            clean_text = re.sub(r'\s*```$', '', clean_text)
                        try:
                            parsed = json.loads(clean_text)
                            if isinstance(parsed, dict):
                                parsed['latency_ms'] = latency
                                if cache_key:
                                    self._cache[cache_key] = parsed
                                return parsed
                        except Exception:
                            json_match = re.search(r'\{[\s\S]*\}', text)
                            if json_match:
                                try:
                                    parsed = json.loads(json_match.group())
                                    if isinstance(parsed, dict):
                                        parsed['latency_ms'] = latency
                                        if cache_key:
                                            self._cache[cache_key] = parsed
                                        return parsed
                                except Exception:
                                    pass
                    
                    if attempt < 2:
                        logger.warning(f'AI JSON parse failed, retrying (attempt {attempt+1})')
                        continue
                    return None
                except httpx.TimeoutException:
                    logger.warning(f'AI JSON request timeout (attempt {attempt+1})')
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return None
                except Exception as e:
                    logger.error(f'AI JSON request error: {type(e).__name__}: {e}')
                    if attempt < 2:
                        await asyncio.sleep(1)
                        continue
                    return None
        return None
    
    async def test_connection(self) -> TestConnectionResponse:
        models_url = self._build_models_url()
        available_models: List[str] = []
        start = time.time()

        # Step 1: Try fetching model list from /v1/models
        try:
            async with httpx.AsyncClient(timeout=min(self.timeout, 8)) as client:
                models_resp = await client.get(models_url, headers=self._headers())
                if models_resp.status_code == 200:
                    data = models_resp.json()
                    raw_models = data.get('data', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                    for m in raw_models:
                        if isinstance(m, dict) and 'id' in m:
                            available_models.append(str(m['id']))
                        elif isinstance(m, str):
                            available_models.append(m)
                elif models_resp.status_code == 401:
                    latency = (time.time() - start) * 1000
                    return TestConnectionResponse(
                        connected=True,
                        model_ok=False,
                        latency_ms=round(latency, 1),
                        error='401 Unauthorized: Invalid API Key',
                        available_models=[]
                    )
        except Exception:
            pass  # Some servers don't support /models, proceed to test chat completion directly

        # Step 2: Test chat completion with selected model or first available model
        test_model = self.model or (available_models[0] if available_models else 'default')
        url = self._build_url()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json={
                        'model': test_model,
                        'messages': [{'role': 'user', 'content': 'Hello'}],
                        'max_tokens': 5,
                        'temperature': 0
                    },
                    headers=self._headers()
                )
            latency = (time.time() - start) * 1000
            if response.status_code == 401:
                return TestConnectionResponse(
                    connected=True,
                    model_ok=False,
                    latency_ms=round(latency, 1),
                    error='401 Unauthorized: Invalid API Key',
                    available_models=available_models
                )
            if response.status_code == 404:
                if available_models:
                    return TestConnectionResponse(
                        connected=True,
                        model_ok=True,
                        latency_ms=round(latency, 1),
                        available_models=available_models
                    )
                return TestConnectionResponse(
                    connected=True,
                    model_ok=False,
                    latency_ms=round(latency, 1),
                    error=f'404 Not Found at {url}',
                    available_models=available_models
                )
            if response.status_code != 200:
                if available_models:
                    return TestConnectionResponse(
                        connected=True,
                        model_ok=True,
                        latency_ms=round(latency, 1),
                        available_models=available_models
                    )
                return TestConnectionResponse(
                    connected=True,
                    model_ok=False,
                    latency_ms=round(latency, 1),
                    error=f'HTTP {response.status_code}: {response.text[:150]}',
                    available_models=available_models
                )
            
            data = response.json()
            model_ok = 'choices' in data
            return TestConnectionResponse(
                connected=True,
                model_ok=model_ok,
                latency_ms=round(latency, 1),
                available_models=available_models
            )
        except httpx.ConnectError as e:
            return TestConnectionResponse(
                connected=False,
                model_ok=False,
                latency_ms=0.0,
                error=f'Server unreachable at {url}. Check Tailscale connection or host IP.',
                available_models=[]
            )
        except httpx.TimeoutException:
            return TestConnectionResponse(
                connected=False,
                model_ok=False,
                latency_ms=0.0,
                error=f'Connection timed out after {self.timeout}s at {url}',
                available_models=available_models
            )
        except Exception as e:
            if available_models:
                return TestConnectionResponse(
                    connected=True,
                    model_ok=True,
                    latency_ms=round((time.time() - start) * 1000, 1),
                    available_models=available_models
                )
            return TestConnectionResponse(
                connected=False,
                model_ok=False,
                latency_ms=0.0,
                error=f'{type(e).__name__}: {str(e)}',
                available_models=[]
            )
