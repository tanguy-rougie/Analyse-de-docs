"""LLM backends: OpenAI, Mistral (API compatible OpenAI), Ollama (local)."""

from __future__ import annotations

import os

import httpx

from src.generation.config import GenerationConfig


def generate_rag_answer(
    messages: list[dict[str, str]],
    config: GenerationConfig,
) -> str:
    """Dispatch to OpenAI, Mistral, or Ollama chat completion."""
    if config.provider == "openai":
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            raise ValueError(
                "OPENAI_API_KEY est requis pour LLM_PROVIDER=openai. "
                "Créez un fichier .env à la racine du dépôt (copie de .env.example) "
                "ou exportez la variable d'environnement."
            )
        return _openai_chat(
            messages, config.openai_model, base_url=None, api_key=key
        )
    if config.provider == "mistral":
        key = os.environ.get("MISTRAL_API_KEY", "").strip()
        if not key:
            raise ValueError(
                "MISTRAL_API_KEY est requis pour LLM_PROVIDER=mistral."
            )
        return _openai_chat(
            messages,
            config.mistral_model,
            base_url=config.mistral_base_url,
            api_key=key,
        )
    if config.provider == "ollama":
        return _ollama_chat(
            messages,
            config.ollama_model,
            config.ollama_base_url,
            timeout=config.ollama_http_timeout,
        )
    raise ValueError(
        f"Unknown LLM_PROVIDER {config.provider!r}; use 'openai', 'mistral', or 'ollama'."
    )


def _openai_chat(
    messages: list[dict[str, str]],
    model: str,
    *,
    base_url: str | None,
    api_key: str | None,
) -> str:
    try:
        from openai import OpenAI
    except ImportError as e:
        raise ImportError(
            "Install the 'openai' package for LLM_PROVIDER=openai or mistral."
        ) from e
    client_kw: dict[str, str] = {}
    if base_url is not None:
        client_kw["base_url"] = base_url.rstrip("/")
    if api_key is not None:
        client_kw["api_key"] = api_key
    client = OpenAI(**client_kw)
    resp = client.chat.completions.create(model=model, messages=messages)
    choice = resp.choices[0]
    content = choice.message.content
    if not content:
        return ""
    return content.strip()


def _ollama_chat(
    messages: list[dict[str, str]],
    model: str,
    base_url: str,
    *,
    timeout: float = 600.0,
) -> str:
    url = f"{base_url.rstrip('/')}/api/chat"
    payload = {"model": model, "messages": messages, "stream": False}
    t = max(30.0, float(timeout))
    try:
        with httpx.Client(timeout=t) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
    except httpx.ConnectError as e:
        raise ValueError(
            f"Impossible de joindre Ollama à {base_url}. "
            "Démarrez Ollama (application ou `ollama serve`), puis vérifiez OLLAMA_BASE_URL."
        ) from e
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ValueError(
                f"Modèle Ollama {model!r} introuvable. "
                f"Installez-le avec : ollama pull {model}"
            ) from e
        raise ValueError(f"Erreur Ollama ({e.response.status_code}) : {e.response.text}") from e
    msg = data.get("message") or {}
    content = msg.get("content", "")
    return content.strip() if isinstance(content, str) else ""
