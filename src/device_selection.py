"""Optional device selection for NEW experiments; existing notebooks are untouched.

PyTorch is imported lazily, so importing this module needs no GPU or torch install.
Explicit accelerator requests fail when unavailable instead of silently changing
an experiment's backend. Auto selection uses CUDA, then MPS, then CPU.
"""


def select_device(preferred="auto"):
    """Return a torch.device for auto/cuda/mps/cpu without allocating tensors."""
    if preferred not in {"auto", "cuda", "mps", "cpu"}:
        raise ValueError("preferred must be one of: auto, cuda, mps, cpu")
    import torch

    if preferred == "cpu":
        return torch.device("cpu")
    if preferred == "cuda" or (preferred == "auto" and torch.cuda.is_available()):
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is unavailable; check the torch build and NVIDIA driver.")
        return torch.device("cuda")
    mps = getattr(getattr(torch, "backends", None), "mps", None)
    available = mps is not None and mps.is_available()
    if preferred == "mps" or (preferred == "auto" and available):
        if not available:
            raise RuntimeError("MPS was requested but is unavailable; check the native ARM64 build and macOS support.")
        return torch.device("mps")
    return torch.device("cpu")
