import sys
from pathlib import Path

ROOT             = Path(__file__).parent.parent
SERVICES_CONF    = ROOT / "services.conf"
LOCAL_ENV        = ROOT / "local" / ".env"
VPS_ENV          = ROOT / "vps"   / ".env"
_DEFAULT_SSH_KEY = Path.home() / ".ssh" / "porthole_do"

def _c(code, t): return f"\033[{code}m{t}\033[0m" if sys.stdout.isatty() else t
green  = lambda t: _c("32", t)
red    = lambda t: _c("31", t)
yellow = lambda t: _c("33", t)
bold   = lambda t: _c("1",  t)
dim    = lambda t: _c("2",  t)
