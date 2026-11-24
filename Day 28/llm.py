"""LLM backend abstraction supporting local and hosted inference providers."""

import json
import os
import re

import httpx

from config import (
    BACKEND,
    HF_4BIT,
    HF_MAX_NEW_TOKENS,
    HF_MODEL,
    MODEL,
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OPENAI_BASE,
    OPENAI_MODEL,
)

_anthropic_client = None
_hf_client = None
_hf_pipe = None


def _build_messages(system: str, user: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _ollama(system: str, user: str, max_tokens: int, json_mode: bool = False) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": _build_messages(system, user),
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.2, "num_ctx": OLLAMA_NUM_CTX},
    }
    if json_mode:
        payload["format"] = "json"
    response = httpx.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=900)
    response.raise_for_status()
    return response.json()["message"]["content"]


def _openai_compat(system: str, user: str, max_tokens: int, json_mode: bool = False) -> str:
    response = httpx.post(
        f"{OPENAI_BASE}/chat/completions",
        json={
            "model": OPENAI_MODEL,
            "messages": _build_messages(system, user),
            "max_tokens": max_tokens,
            "temperature": 0.2,
        },
        timeout=900,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _hf_local(system: str, user: str, max_tokens: int, json_mode: bool = False) -> str:
    global _hf_pipe
    if _hf_pipe is None:
        import torch
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            pipeline,
        )

        quant_config = None
        if HF_4BIT:
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
        tokenizer = AutoTokenizer.from_pretrained(HF_MODEL)
        model = AutoModelForCausalLM.from_pretrained(
            HF_MODEL,
            quantization_config=quant_config,
            device_map="auto",
            torch_dtype=torch.float16,
        )
        _hf_pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)

    outputs = _hf_pipe(
        _build_messages(system, user),
        max_new_tokens=min(max_tokens, HF_MAX_NEW_TOKENS),
        do_sample=False,
        return_full_text=False,
    )
    generated = outputs[0]["generated_text"]
    return generated if isinstance(generated, str) else generated[-1]["content"]


def _hf_api(system: str, user: str, max_tokens: int, json_mode: bool = False) -> str:
    global _hf_client
    if _hf_client is None:
        from huggingface_hub import InferenceClient

        _hf_client = InferenceClient(model=HF_MODEL, token=os.getenv("HF_TOKEN"))
    response = _hf_client.chat_completion(
        messages=_build_messages(system, user), max_tokens=max_tokens, temperature=0.2
    )
    return response.choices[0].message.content


def _anthropic(system: str, user: str, max_tokens: int, json_mode: bool = False) -> str:
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import Anthropic

        _anthropic_client = Anthropic()
    response = _anthropic_client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


_BACKENDS = {
    "ollama": _ollama,
    "openai_compat": _openai_compat,
    "hf_local": _hf_local,
    "hf_api": _hf_api,
    "anthropic": _anthropic,
}


def chat(system: str, user: str, max_tokens: int = 4000, json_mode: bool = False) -> str:
    """Send a chat prompt to the configured LLM backend."""
    backend_fn = _BACKENDS.get(BACKEND)
    if backend_fn is None:
        raise ValueError(f"Unsupported RA_BACKEND '{BACKEND}'. Expected one of {sorted(_BACKENDS)}.")
    return backend_fn(system, user, max_tokens, json_mode)


def _extract_first_json_object(text: str) -> dict:
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch in "{[":
            try:
                parsed, _ = decoder.raw_decode(text[idx:])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue
    raise json.JSONDecodeError("No valid JSON object found in model output", text, 0)


def _parse_json(raw: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except json.JSONDecodeError:
        return _extract_first_json_object(cleaned)


def chat_json(system: str, user: str, max_tokens: int = 4000) -> dict:
    """Request a JSON dictionary from the LLM, retrying once with a repair prompt on failure."""
    json_system = f"{system}\n\nReturn ONLY valid JSON. No prose, no markdown fences."
    raw = chat(json_system, user, max_tokens, json_mode=True)
    try:
        return _parse_json(raw)
    except json.JSONDecodeError:
        repaired = chat(
            "Fix this into valid JSON. Return only the JSON.", raw, max_tokens, json_mode=True
        )
        return _parse_json(repaired)
