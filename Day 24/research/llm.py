import json
import logging
import os
import re
import time

import httpx

from research.config import (
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

logger = logging.getLogger(__name__)

_anthropic_client = None
_hf_client = None
_hf_pipe = None


def _msgs(system, user):
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ---------- local backends ----------

def _ollama(system, user, max_tokens, json_mode=False):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": _msgs(system, user),
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.2, "num_ctx": OLLAMA_NUM_CTX},
    }
    if json_mode:
        payload["format"] = "json"  # forces valid JSON output
    r = httpx.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=900)
    r.raise_for_status()
    return r.json()["message"]["content"]


def _openai_compat(system, user, max_tokens, json_mode=False):
    r = httpx.post(
        f"{OPENAI_BASE}/chat/completions",
        json={
            "model": OPENAI_MODEL,
            "messages": _msgs(system, user),
            "max_tokens": max_tokens,
            "temperature": 0.2,
        },
        timeout=900,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _hf_local(system, user, max_tokens, json_mode=False):
    global _hf_pipe
    if _hf_pipe is None:
        import torch
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            pipeline,
        )

        quant = None
        if HF_4BIT:
            quant = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
        tok = AutoTokenizer.from_pretrained(HF_MODEL)
        model = AutoModelForCausalLM.from_pretrained(
            HF_MODEL,
            quantization_config=quant,
            device_map="auto",
            torch_dtype=torch.float16,
        )
        _hf_pipe = pipeline("text-generation", model=model, tokenizer=tok)
    out = _hf_pipe(
        _msgs(system, user),
        max_new_tokens=min(max_tokens, HF_MAX_NEW_TOKENS),
        do_sample=False,
        return_full_text=False,
    )
    gen = out[0]["generated_text"]
    return gen if isinstance(gen, str) else gen[-1]["content"]


# ---------- hosted backends (optional) ----------

def _hf_api(system, user, max_tokens, json_mode=False):
    global _hf_client
    if _hf_client is None:
        from huggingface_hub import InferenceClient
        _hf_client = InferenceClient(model=HF_MODEL, token=os.getenv("HF_TOKEN"))
    r = _hf_client.chat_completion(
        messages=_msgs(system, user), max_tokens=max_tokens, temperature=0.2
    )
    return r.choices[0].message.content


def _anthropic(system, user, max_tokens, json_mode=False):
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import Anthropic
        _anthropic_client = Anthropic()
    r = _anthropic_client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in r.content if b.type == "text")


_BACKENDS = {
    "ollama": _ollama,
    "openai_compat": _openai_compat,
    "hf_local": _hf_local,
    "hf_api": _hf_api,
    "anthropic": _anthropic,
}


def chat(system: str, user: str, max_tokens: int = 4000, json_mode: bool = False) -> str:
    fn = _BACKENDS.get(BACKEND)
    if fn is None:
        raise ValueError(f"Unknown RA_BACKEND '{BACKEND}'. Valid values: {', '.join(_BACKENDS)}")
    start = time.perf_counter()
    try:
        out = fn(system, user, max_tokens, json_mode)
    except Exception:
        logger.exception("LLM call failed (backend=%s)", BACKEND)
        raise
    logger.info(
        "LLM call ok (backend=%s, json=%s, %.1fs, %d chars)",
        BACKEND, json_mode, time.perf_counter() - start, len(out),
    )
    return out


def _parse_json(raw: str) -> dict:
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def chat_json(system: str, user: str, max_tokens: int = 4000) -> dict:
    system += "\n\nReturn ONLY valid JSON. No prose, no markdown fences."
    raw = chat(system, user, max_tokens, json_mode=True)
    try:
        return _parse_json(raw)
    except json.JSONDecodeError:
        logger.warning("Model returned invalid JSON; asking it to repair")
        fix = chat("Fix this into valid JSON. Return only the JSON.", raw, max_tokens, json_mode=True)
        return _parse_json(fix)
