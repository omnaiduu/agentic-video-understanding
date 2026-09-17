"""HF ids and Modal app names for the E4B vs 12B A/B. Not imported by the loop."""

E4B_HF_ID = "google/gemma-4-E4B-it"
TWELVE_B_HF_ID = "google/gemma-4-12B-it"
# Official Google QAT W4A16 (compressed-tensors). BF16 12B does not fit an L4.
TWELVE_B_WEIGHTS = "google/gemma-4-12B-it-qat-w4a16-ct"
E4B_MODAL_APP = "agentic-video-brain"
E4B_THINKING_MODAL_APP = "agentic-video-brain-e4b-thinking"
TWELVE_B_MODAL_APP = "agentic-video-brain-12b"
EXAM_TAPE_ID = "c1d9beb7-5465-4f47-9d53-2d6b299104b5"
