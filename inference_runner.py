"""Launch Nara's unmodified synthesis script with optional ONNX Runtime CUDA.

This adapter is intentionally separate from upstream files. It changes only
ONNX Runtime's session provider preference at creation time.
"""
import argparse
import runpy
import sys
from pathlib import Path


def configure_provider(mode: str):
    import onnxruntime as ort
    available = ort.get_available_providers()
    has_cuda = "CUDAExecutionProvider" in available
    if mode == "cuda" and not has_cuda:
        raise RuntimeError(
            "NVIDIA CUDA runtime is unavailable. Install GPU runtime in the app, "
            "and ensure your NVIDIA drivers, CUDA and cuDNN match your ONNX Runtime version. "
            f"Detected ONNX providers: {', '.join(available)}"
        )
    use_cuda = (mode == "cuda") or (mode == "auto" and has_cuda)
    providers_preference = ["CUDAExecutionProvider", "CPUExecutionProvider"] if use_cuda else ["CPUExecutionProvider"]
    print(f"mimo-myanmar: selected {'GPU + CPU fallback' if use_cuda else 'CPU'}", flush=True)
    print(f"mimo-myanmar: available providers: {', '.join(available)}", flush=True)

    base = ort.InferenceSession

    def session(path_or_bytes, sess_options=None, providers=None, provider_options=None, **kwargs):
        # Override the provider list, leaving the official script unmodified.
        # Explicit named parameters avoid collisions with upstream positional args.
        obj = base(path_or_bytes, sess_options=sess_options,
                   providers=providers_preference,
                   provider_options=None, **kwargs)
        active = obj.get_providers()
        if use_cuda and "CUDAExecutionProvider" not in active:
            if mode == "cuda":
                raise RuntimeError(
                    "ONNX Runtime could not activate CUDA for the model. "
                    "Check driver/CUDA/cuDNN compatibility and GPU memory. "
                    f"Active providers: {active}"
                )
            print("mimo-myanmar: CUDA was unavailable for a session; using CPU.", flush=True)
        return obj

    ort.InferenceSession = session


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--backend", choices=["auto", "cpu", "cuda"], default="auto")
    options, rest = parser.parse_known_args()
    script = Path(__file__).resolve().parent / "model" / "synthesize.py"
    if not script.exists():
        raise SystemExit("Nara Mini is not installed. Use Download voices in the app.")
    try:
        configure_provider(options.backend)
    except ModuleNotFoundError as exc:
        if exc.name == "onnxruntime":
            raise SystemExit(
                "ONNX Runtime is missing. Close mimo-myanmar and reopen "
                "Start_mimo-myanmar.bat to repair it."
            ) from None
        raise SystemExit(str(exc)) from None
    except Exception as exc:
        raise SystemExit(str(exc))
    sys.argv = [str(script), *rest]
    sys.path.insert(0, str(script.parent))
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
