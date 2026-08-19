# Runtime constraints

The two files in this directory are tested CPython 3.12 constraints, not
portable virtual environments. Provision them separately:

    python -m pip install -r requirements/nougat.txt
    python -m pip install -r requirements/docling.txt

The bootstrap script does this in .runtime/nougat and .runtime/docling.
Exact pins keep cache keys and conversions reproducible on the tested CPU
baseline.

## PyTorch platform guidance

- CPU: use the pinned torch and torchvision lines as written.
- macOS arm64/x86_64: the pinned PyTorch wheels provide the CPU/MPS baseline
  where supported by the installed macOS and hardware.
- Linux or Windows with CUDA: select a matching torch/torchvision pair from
  the official PyTorch installation selector, then replace only those two
  lines in the affected environment's constraints.
- WSL2 CUDA: install the Linux CUDA wheel inside WSL and verify the host NVIDIA
  driver/CUDA passthrough independently.

Do not mix Nougat and Docling into one environment. Their transitive
dependencies can resolve differently even when the top-level torch versions
match. After changing a wheel, rerun check_deps.py and record the resulting
versions in the manifest.

Official selector:
https://pytorch.org/get-started/locally/
