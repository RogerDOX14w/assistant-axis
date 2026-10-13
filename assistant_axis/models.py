"""
Model configuration utilities.

This module provides configuration lookup for known models, including
project-specific values like target layers for axis computation.

For model loading, use ProbingModel from assistant_axis.internals instead.

Example:
    from assistant_axis import get_config
    from assistant_axis.internals import ProbingModel

    pm = ProbingModel("google/gemma-2-27b-it")
    config = get_config("google/gemma-2-27b-it")
    target_layer = config["target_layer"]
"""


MODEL_CONFIGS = {
    # Format: model_name -> {target_layer, total_layers, short_name, capping_config, capping_experiment}
    # target_layer is the recommended layer for axis computation (typically ~middle)
    # capping_config is the HuggingFace path to the capping config file
    # capping_experiment is the recommended experiment ID for activation capping
    "google/gemma-2-27b-it": {
        "target_layer": 22,
        "total_layers": 46,
        "short_name": "Gemma",
    },
    "Qwen/Qwen3-32B": {
        "target_layer": 32,
        "total_layers": 64,
        "short_name": "Qwen",
        "capping_config": "qwen-3-32b/capping_config.pt",
        "capping_experiment": "layers_46:54-p0.25",
    },
    "meta-llama/Llama-3.3-70B-Instruct": {
        "target_layer": 40,
        "total_layers": 80,
        "short_name": "Llama",
        "capping_config": "llama-3.3-70b/capping_config.pt",
        "capping_experiment": "layers_56:72-p0.25",
    },
}


def get_config(model_name: str, *, with_family: bool = False) -> dict:
    """
    Get configuration for a model.

    Args:
        model_name: HuggingFace model name
        with_family: also return ``"family"``, the model's row of the family
            table (:func:`assistant_axis.model_families.family_for_model`, read
            from its ``config.json``; an unknown ``model_type`` raises).  The
            two tables are kept apart on purpose (multi-model plan § 5.2, § 15
            Q1): this one is keyed by the exact repository id and holds
            per-model facts (target layer, layer count, short name, capping);
            the family table is keyed on ``config.model_type`` and holds what
            every checkpoint of an architecture shares.

    Returns:
        Dict with target_layer, total_layers, and short_name (and ``family``
        when asked).  If model is not in known configs, infers values from
        model architecture.

    TODO (multi-model plan § 10 task 11, § 15 Q6): stub rows
    (``short_name``, ``total_layers``, ``target_layer = total // 2``) for the
    other-family models, once Roger names them.
    """
    config = _base_config(model_name)
    if with_family:
        from .model_families import family_for_model
        config["family"] = family_for_model(model_name)
    return config


def _base_config(model_name: str) -> dict:
    if model_name in MODEL_CONFIGS:
        return MODEL_CONFIGS[model_name].copy()

    # Try to infer config from model
    try:
        from transformers import AutoConfig
        config = AutoConfig.from_pretrained(model_name)
        total_layers = config.num_hidden_layers
        target_layer = total_layers // 2  # Default to middle layer

        # Infer short name from model name
        model_lower = model_name.lower()
        if "gemma" in model_lower:
            short_name = "Gemma"
        elif "qwen" in model_lower:
            short_name = "Qwen"
        elif "llama" in model_lower:
            short_name = "Llama"
        elif "mistral" in model_lower:
            short_name = "Mistral"
        else:
            short_name = model_name.split("/")[-1].split("-")[0]

        return {
            "target_layer": target_layer,
            "total_layers": total_layers,
            "short_name": short_name,
        }
    except Exception as e:
        raise ValueError(f"Could not infer config for model {model_name}: {e}")
