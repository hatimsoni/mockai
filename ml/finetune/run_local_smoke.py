"""Execute the notebook's code cells locally on CPU with a tiny subset (SMOKE_TEST=1).

    python ml/finetune/run_local_smoke.py

Purpose: catch bugs before spending a Colab session. Skips cells tagged "colab-only"
(pip installs, GGUF export, downloads). Downloads Qwen2.5-0.5B-Instruct (~1 GB) on first run;
needs ~4 GB RAM; takes a few minutes. Metrics from a smoke run are meaningless (12 test rows).
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
NB = HERE / "lora_qwen_scoring.ipynb"


def main() -> None:
    os.environ["SMOKE_TEST"] = "1"
    os.environ["DATA_DIR"] = str((HERE.parent / "data").resolve())
    nb = json.loads(NB.read_text(encoding="utf-8"))
    workdir = tempfile.mkdtemp(prefix="lora-smoke-")
    os.chdir(workdir)  # lora_metrics.json etc. land here, not in the repo
    ns: dict = {"__name__": "__main__"}
    for cell in nb["cells"]:
        if cell["cell_type"] != "code" or "colab-only" in cell.get("metadata", {}).get("tags", []):
            continue
        src = "".join(cell["source"])
        print(f"\n### running {cell['id']}: {src.splitlines()[0][:70]}")
        exec(compile(src, cell["id"], "exec"), ns)  # noqa: S102 - our own notebook
    print(f"\nSMOKE TEST PASSED (outputs in {workdir})")


if __name__ == "__main__":
    main()
