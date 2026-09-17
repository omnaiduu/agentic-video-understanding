"""Patch vLLM 0.29 dummy-audio profiling for Gemma 4 Unified.

Tower Gemma 4 (E4B) uses a mel feature extractor with `fft_length`.
Encoder-free Unified 12B chunks raw waveform and only has
`audio_samples_per_token`. Profiling then crashes:

    AttributeError: 'Gemma4UnifiedAudioFeatureExtractor' object has no
    attribute 'fft_length'

This file is copied into the 12B Modal image and run at build time.
E4B keeps the unpatched image.
"""

from __future__ import annotations

from pathlib import Path

OLD = "audio_len = processor.feature_extractor.fft_length"
NEW = (
    "audio_len = getattr(processor.feature_extractor, 'fft_length', None) "
    "or getattr(processor.feature_extractor, 'audio_samples_per_token', 640)"
)


def main() -> None:
    root = Path("/usr/local/lib/python3.12/site-packages/vllm")
    hits = list(root.glob("**/gemma4_mm.py"))
    if not hits:
        raise SystemExit("vLLM gemma4_mm.py not found")
    patched = 0
    for path in hits:
        text = path.read_text()
        if OLD not in text:
            continue
        path.write_text(text.replace(OLD, NEW))
        patched += 1
        print(f"patched {path}")
    if patched == 0:
        raise SystemExit("fft_length dummy line not found in gemma4_mm.py")


if __name__ == "__main__":
    main()
