# SPDX-License-Identifier: AGPL-3.0-or-later
"""Choice sets for the AI catalog + placement models. ``architecture`` and ``parameter_count`` are
deliberately free-form ``CharField``s (new architectures appear constantly — a closed set would
force a refactor per model, violating extensibility); the bounded axes below are real choice sets."""
from utilities.choices import ChoiceSet


class ModalityChoices(ChoiceSet):
    """What a model consumes/produces — drives which backend + planning rules apply."""
    TEXT = "text"
    VISION = "vision"
    EMBEDDING = "embedding"
    IMAGE_GEN = "image_gen"
    AUDIO_STT = "audio_stt"
    AUDIO_TTS = "audio_tts"
    CHOICES = [
        (TEXT, "Text", "blue"),
        (VISION, "Vision", "indigo"),
        (EMBEDDING, "Embedding", "cyan"),
        (IMAGE_GEN, "Image generation", "purple"),
        (AUDIO_STT, "Audio (STT)", "teal"),
        (AUDIO_TTS, "Audio (TTS)", "green"),
    ]


class ModelSourceTypeChoices(ChoiceSet):
    """How ``ModelCatalog.source`` is resolved — a *reference* to the weights, never the weights."""
    HF_REPO = "hf_repo"
    OLLAMA_TAG = "ollama_tag"
    URL = "url"
    CHOICES = [
        (HF_REPO, "HuggingFace repo", "yellow"),
        (OLLAMA_TAG, "Ollama tag", "gray"),
        (URL, "URL", "blue"),
    ]


class QuantizationChoices(ChoiceSet):
    """Weight quantization of a variant (the ``family:quant`` axis). Extensible — add rows as new
    quant schemes land; the set is intentionally broad rather than per-backend."""
    FP16 = "fp16"
    BF16 = "bf16"
    FP8 = "fp8"
    Q8_0 = "q8_0"
    Q6_K_L = "q6_k_l"
    Q6_K = "q6_k"
    Q5_K_M = "q5_k_m"
    Q4_K_XL = "q4_k_xl"
    Q4_K_M = "q4_k_m"
    IQ4_XS = "iq4_xs"
    Q4_0 = "q4_0"
    Q3_K_M = "q3_k_m"
    AWQ = "awq"
    GPTQ = "gptq"
    CHOICES = [
        (FP16, "FP16", "red"),
        (BF16, "BF16", "red"),
        (FP8, "FP8", "orange"),
        (Q8_0, "Q8_0", "orange"),
        (Q6_K_L, "Q6_K_L", "yellow"),
        (Q6_K, "Q6_K", "yellow"),
        (Q5_K_M, "Q5_K_M", "yellow"),
        (Q4_K_XL, "Q4_K_XL", "green"),
        (Q4_K_M, "Q4_K_M", "green"),
        (IQ4_XS, "IQ4_XS", "green"),
        (Q4_0, "Q4_0", "green"),
        (Q3_K_M, "Q3_K_M", "gray"),
        (AWQ, "AWQ", "purple"),
        (GPTQ, "GPTQ", "purple"),
    ]


class DTypeChoices(ChoiceSet):
    """Runtime compute dtype passed to the backend (vLLM ``--dtype`` / SGLang equivalent)."""
    AUTO = "auto"
    FLOAT16 = "float16"
    BFLOAT16 = "bfloat16"
    FLOAT32 = "float32"
    FP8 = "fp8"
    CHOICES = [
        (AUTO, "Auto", "gray"),
        (FLOAT16, "float16", "blue"),
        (BFLOAT16, "bfloat16", "blue"),
        (FLOAT32, "float32", "indigo"),
        (FP8, "fp8", "orange"),
    ]


class KVCacheQuantChoices(ChoiceSet):
    """KV-cache quantization (vLLM ``--kv-cache-dtype``). ``auto`` = backend default (unquantized)."""
    AUTO = "auto"
    FP8 = "fp8"
    INT8 = "int8"
    CHOICES = [
        (AUTO, "Auto", "gray"),
        (FP8, "FP8", "orange"),
        (INT8, "INT8", "yellow"),
    ]


class DeploymentStatusChoices(ChoiceSet):
    """Lifecycle of an :class:`InferenceDeployment` / :class:`GatewayRoute`. NetBox stores the
    *planned* state; ``active`` means the renderer has materialized it (live health is monitoring)."""
    PLANNED = "planned"
    ACTIVE = "active"
    INACTIVE = "inactive"
    CHOICES = [
        (PLANNED, "Planned", "blue"),
        (ACTIVE, "Active", "green"),
        (INACTIVE, "Inactive", "gray"),
    ]
