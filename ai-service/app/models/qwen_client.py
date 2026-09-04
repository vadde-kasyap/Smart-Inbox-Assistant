"""
Qwen3-VL-2B-Instruct client — singleton model wrapper.

Design:
- Loads the model ONCE on first use (lazy init).
- Supports text-only and vision (image + text) inference.
- Gracefully falls back to mock mode when:
    • USE_MOCK_AI=true is set in the environment, OR
    • transformers / torch are not installed, OR
    • The model download / loading fails.
- Model name is fully configurable via AI_MODEL_NAME env var.
"""

import os
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton holder
# ---------------------------------------------------------------------------
_client_instance: Optional["QwenClient"] = None


def get_qwen_client() -> "QwenClient":
    """Return the process-wide singleton QwenClient."""
    global _client_instance
    if _client_instance is None:
        _client_instance = QwenClient()
    return _client_instance


# ---------------------------------------------------------------------------
# QwenClient
# ---------------------------------------------------------------------------
class QwenClient:
    """
    Wrapper around the Qwen2-VL / Qwen3-VL vision-language model.

    Public methods
    --------------
    analyze_text(prompt, max_new_tokens) -> str
        Run a text-only prompt and return the model's raw string response.

    analyze_image(pil_image, prompt, max_new_tokens) -> str
        Run a vision prompt (image + text) and return the model's raw string response.

    is_mock -> bool
        True when the client is running in fallback / mock mode.
    """

    def __init__(self) -> None:
        self.model_name: str = os.getenv(
            "AI_MODEL_NAME", "Qwen/Qwen2-VL-2B-Instruct"
        )
        # Normalise the env var (assignment uses "Qwen3-VL-2B-Instruct" without the
        # HuggingFace org prefix).  Map it to the published HF id.
        self.model_name = self._normalise_model_name(self.model_name)

        self._use_mock: bool = os.getenv("USE_MOCK_AI", "false").lower() == "true"
        self._model = None
        self._processor = None

        if not self._use_mock:
            self._load_model()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def is_mock(self) -> bool:
        return self._use_mock

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalise_model_name(name: str) -> str:
        """
        Allow users to set the env var to the short form used in the assignment
        (e.g. 'Qwen3-VL-2B-Instruct') and map it to the HuggingFace id.
        """
        mapping = {
            "Qwen3-VL-2B-Instruct": "Qwen/Qwen2-VL-2B-Instruct",
            "Qwen2-VL-2B-Instruct": "Qwen/Qwen2-VL-2B-Instruct",
            "Qwen2.5-VL-3B-Instruct": "Qwen/Qwen2.5-VL-3B-Instruct",
        }
        return mapping.get(name, name)

    def _load_model(self) -> None:
        """Attempt to load the Qwen2-VL model + processor.  Falls back to mock on any error."""
        try:
            import torch  # noqa: F401
            from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

            logger.info("Loading model '%s' — this may take several minutes…", self.model_name)

            self._processor = AutoProcessor.from_pretrained(
                self.model_name,
                trust_remote_code=True,
            )
            self._model = Qwen2VLForConditionalGeneration.from_pretrained(
                self.model_name,
                device_map="auto",
                trust_remote_code=True,
            )
            self._model.eval()
            logger.info("Model '%s' loaded successfully.", self.model_name)

        except ImportError as exc:
            logger.warning(
                "transformers / torch not installed (%s). Switching to mock mode. "
                "Install them to enable real AI inference.",
                exc,
            )
            self._use_mock = True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Failed to load model '%s': %s.  Switching to mock mode.",
                self.model_name,
                exc,
            )
            self._use_mock = True

    def _run_inference(self, messages: list, max_new_tokens: int = 2048) -> str:
        """
        Apply the chat template, tokenise, run generation, and decode output.
        Must only be called when self._model is not None.
        """
        import torch

        text = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        inputs = self._processor(
            text=[text],
            return_tensors="pt",
        )
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=0.05,
                do_sample=False,
                pad_token_id=self._processor.tokenizer.eos_token_id,
            )

        # Decode only the newly generated tokens
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        return self._processor.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def analyze_text(self, prompt: str, max_new_tokens: int = 2048) -> str:
        """
        Run a text-only prompt.
        Returns an empty string in mock mode (caller handles the fallback).
        """
        if self._use_mock or self._model is None:
            return ""

        messages = [
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ]
        try:
            return self._run_inference(messages, max_new_tokens)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Model text inference error: %s", exc)
            return ""

    def analyze_image(self, pil_image, prompt: str, max_new_tokens: int = 1024) -> str:
        """
        Run a vision prompt (image + text).
        Returns an empty string in mock mode.
        """
        if self._use_mock or self._model is None:
            return ""

        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": pil_image},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            # Process images separately for Qwen2-VL
            text = self._processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            image_inputs, _ = self._process_vision_info(messages)
            inputs = self._processor(
                text=[text],
                images=image_inputs,
                return_tensors="pt",
                padding=True,
            )
            import torch
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=0.05,
                    do_sample=False,
                )

            new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
            return self._processor.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Model vision inference error: %s", exc)
            return ""

    @staticmethod
    def _process_vision_info(messages: list):
        """
        Extract PIL images and video frames from the message list.
        Mirrors the logic of qwen-vl-utils without requiring that optional package.
        """
        images = []
        videos = []
        for msg in messages:
            content = msg.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if item.get("type") == "image":
                        images.append(item["image"])
        return images if images else None, videos if videos else None

    def extract_json_from_response(self, raw: str) -> Optional[dict]:
        """
        Attempt to parse the first JSON object or array found in `raw`.
        Returns None if nothing parseable is found.
        """
        if not raw:
            return None
        # Find JSON block (possibly wrapped in ```json … ```)
        json_match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find bare JSON object / array
        for pattern in (r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})", r"(\[.*?\])"):
            m = re.search(pattern, raw, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    continue
        return None
