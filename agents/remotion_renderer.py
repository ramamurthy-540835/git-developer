import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any


def render_with_remotion(plan: Dict[str, Any], product_name: str, output_mp4_path: str) -> str:
    root = Path(__file__).resolve().parents[1] / "video" / "remotion"
    props_path = root / "props.json"
    out_path = root / "out.mp4"
    payload = {"plan": plan, "productName": product_name}
    props_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    cmd = ["npm", "run", "render"]
    proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Remotion render failed: {proc.stderr or proc.stdout}")
    if not out_path.exists():
        raise RuntimeError("Remotion output out.mp4 not found.")

    out_final = Path(output_mp4_path)
    out_final.parent.mkdir(parents=True, exist_ok=True)
    out_final.write_bytes(out_path.read_bytes())
    return str(out_final)

