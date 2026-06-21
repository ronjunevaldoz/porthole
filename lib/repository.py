from pathlib import Path

from .models import Service
from .utils import ROOT, LOCAL_ENV, VPS_ENV, SERVICES_CONF, _DEFAULT_SSH_KEY

FRPC_INI    = ROOT / "local" / "frpc.ini"
VPS_COMPOSE = ROOT / "vps"   / "docker-compose.yml"


def load_env(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def save_env(path: Path, updates: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines   = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    written = set()
    out     = []
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k = s.split("=", 1)[0].strip()
            if k in updates:
                out.append(f"{k}={updates[k]}")
                written.add(k)
                continue
        out.append(line)
    for k, v in updates.items():
        if k not in written:
            out.append(f"{k}={v}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")

def get_ssh_key() -> Path:
    env = load_env(LOCAL_ENV)
    return Path(env["SSH_KEY"]).expanduser() if env.get("SSH_KEY") else _DEFAULT_SSH_KEY

def load_config() -> dict:
    return {**load_env(LOCAL_ENV), **load_env(VPS_ENV)}

def load_services() -> list[Service]:
    services = []
    for line in SERVICES_CONF.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = [p.strip() for p in s.split(":")]
        if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
            continue
        services.append(Service(
            name        = parts[0],
            local_port  = int(parts[1]),
            remote_port = int(parts[2]),
            local_host  = parts[3] if len(parts) > 3 else "",
        ))
    return services
