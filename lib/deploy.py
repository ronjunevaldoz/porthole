import socket
import subprocess
import urllib.request
from pathlib import Path

from .core import get_ssh_key, green, yellow

def run(cmd: str, silent=False):
    kw = dict(shell=True, capture_output=True, text=True) if silent else dict(shell=True)
    return subprocess.run(cmd, **kw)

def ssh_cmd(host, cmd):
    key = get_ssh_key()
    return run(f'ssh -i "{key}" -o StrictHostKeyChecking=no root@{host} "{cmd}"')

def scp_file(src: Path, host, remote_path):
    key = get_ssh_key()
    return run(f'scp -i "{key}" "{src}" root@{host}:{remote_path}')

def scp_str(content: str, host, remote_path):
    key = get_ssh_key()
    return subprocess.run(
        f'ssh -i "{key}" -o StrictHostKeyChecking=no root@{host} "cat > {remote_path}"',
        input=content, shell=True, text=True,
    )

def port_open(host, port, timeout=3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def https_check(domain, path="/") -> bool:
    try:
        import ssl
        ctx = ssl.create_default_context()
        urllib.request.urlopen(f"https://{domain}{path}", context=ctx, timeout=5)
        return True
    except Exception:
        return False

def duckdns_update(domain, vps_ip, token) -> bool:
    subdomain = domain.replace(".duckdns.org", "")
    url = f"https://www.duckdns.org/update?domains={subdomain}&token={token}&ip={vps_ip}"
    try:
        resp = urllib.request.urlopen(url, timeout=10).read().decode().strip()
        return resp == "OK"
    except Exception:
        return False

def sync_firewall(services, extra_ports=None):
    result = run("doctl compute firewall list --format ID,Name --no-header", silent=True)
    if result.returncode != 0:
        print(f"  {yellow('⚠')}  doctl not available — skipping firewall sync")
        return
    fw_lines = [l for l in result.stdout.splitlines() if "porthole-fw" in l]
    if not fw_lines:
        print(f"  {yellow('⚠')}  porthole-fw firewall not found — skipping firewall sync")
        return
    fw_id  = fw_lines[0].split()[0]
    fixed  = [22, 7000, 7500] + (extra_ports or [])
    rules  = " ".join(f"protocol:tcp,ports:{p},address:0.0.0.0/0,address:::/0" for p in fixed)
    rules += " " + " ".join(
        f"protocol:tcp,ports:{svc.remote_port},address:0.0.0.0/0,address:::/0"
        for svc in services
    )
    out = "protocol:tcp,ports:all,address:0.0.0.0/0,address:::/0 protocol:udp,ports:all,address:0.0.0.0/0,address:::/0"
    run(f'doctl compute firewall update {fw_id} --name porthole-fw --inbound-rules "{rules}" --outbound-rules "{out}"', silent=True)
    all_ports = fixed + [svc.remote_port for svc in services]
    print(f"  {green('✓')}  firewall synced ({', '.join(map(str, all_ports))})")
