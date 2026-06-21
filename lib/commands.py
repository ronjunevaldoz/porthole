import secrets
import sys
from pathlib import Path

from .utils import green, red, yellow, bold, dim, LOCAL_ENV, VPS_ENV, SERVICES_CONF
from .repository import load_env, save_env, get_ssh_key, load_config, load_services, FRPC_INI, VPS_COMPOSE
from .templates import gen_frpc_ini, gen_vps_compose, gen_nginx_conf
from .deploy import run, ssh_cmd, scp_file, scp_str, port_open, https_check, duckdns_update, sync_firewall


def cmd_config(args):
    env_local = load_env(LOCAL_ENV)
    changed   = False

    if args.vps:
        save_env(LOCAL_ENV, {"VPS_HOST": args.vps})
        print(f"  {green('✓')}  VPS_HOST       →  {bold(args.vps)}")
        changed = True
    if args.token:
        save_env(LOCAL_ENV, {"FRP_TOKEN": args.token})
        save_env(VPS_ENV,   {"FRP_TOKEN": args.token})
        print(f"  {green('✓')}  FRP_TOKEN updated")
        changed = True
    if args.rotate_token:
        token = secrets.token_hex(32)
        save_env(LOCAL_ENV, {"FRP_TOKEN": token})
        save_env(VPS_ENV,   {"FRP_TOKEN": token})
        print(f"  {green('✓')}  FRP_TOKEN rotated  →  {token}")
        print(f"  {yellow('!')}  Run 'python porthole.py sync' to apply")
        changed = True
    if args.dashboard:
        save_env(VPS_ENV, {"DASHBOARD_PWD": args.dashboard})
        print(f"  {green('✓')}  DASHBOARD_PWD updated")
        changed = True
    if args.domain:
        save_env(VPS_ENV, {"DOMAIN": args.domain})
        print(f"  {green('✓')}  DOMAIN         →  {bold(args.domain)}")
        print(f"  {dim('→')}  Point {args.domain} to {env_local.get('VPS_HOST', '<VPS_IP>')} in your DNS, then run: python porthole.py secure setup")
        changed = True
    if args.email:
        save_env(VPS_ENV, {"EMAIL": args.email})
        print(f"  {green('✓')}  EMAIL          →  {bold(args.email)}")
        changed = True
    if args.ssh_key:
        save_env(LOCAL_ENV, {"SSH_KEY": args.ssh_key})
        print(f"  {green('✓')}  SSH_KEY        →  {bold(args.ssh_key)}")
        changed = True
    if args.duckdns_token:
        save_env(VPS_ENV, {"DUCKDNS_TOKEN": args.duckdns_token})
        print(f"  {green('✓')}  DUCKDNS_TOKEN updated")
        changed = True

    if not changed:
        env      = load_config()
        vps      = env.get("VPS_HOST",      dim("not set"))
        token    = env.get("FRP_TOKEN",     "")
        dash     = env.get("DASHBOARD_PWD", "")
        domain   = env.get("DOMAIN",        dim("not set"))
        email    = env.get("EMAIL",         dim("not set"))
        key      = env.get("SSH_KEY", str(Path.home() / ".ssh" / "porthole_do"))
        key_ok   = Path(key).expanduser().exists()
        ddns_tok = env.get("DUCKDNS_TOKEN", "")
        token_d  = (token[:8] + "..." + token[-4:]) if token else dim("not set")
        dash_d   = "*" * 8 if dash else dim("not set")
        ddns_d   = ("*" * 6 + ddns_tok[-4:]) if ddns_tok else dim("not set")
        mode     = green("HTTPS ✓") if env.get("DOMAIN") else yellow("HTTP (non-secure)")

        print(f"\n  {bold('Current config')}\n")
        print(f"  {'VPS_HOST':<18}  {bold(vps)}")
        print(f"  {'FRP_TOKEN':<18}  {token_d}  {dim('(masked)')}")
        print(f"  {'DASHBOARD_PWD':<18}  {dash_d}")
        print(f"  {'DOMAIN':<18}  {domain}")
        print(f"  {'DUCKDNS_TOKEN':<18}  {ddns_d}")
        print(f"  {'EMAIL':<18}  {email}")
        print(f"  {'SSH_KEY':<18}  {key}  {green('(found)') if key_ok else red('(not found)')}")
        print(f"  {'MODE':<18}  {mode}")
        print()
        if env.get("DOMAIN"):
            print(f"  {dim('HTTPS base URL:')}  https://{env['DOMAIN']}/<service>/")
        print(f"  {dim('Dashboard:')}       http://{env.get('VPS_HOST','?')}:7500")
        print()

def cmd_list(_args):
    services = load_services()
    env      = load_config()
    vps      = env.get("VPS_HOST", dim("not set"))
    domain   = env.get("DOMAIN", "")
    print(f"\n  VPS: {bold(vps)}")
    if domain:
        print(f"  Domain: {bold(domain)}  {green('(HTTPS)')}")
    print()
    print(f"  {bold('NAME'):<26}  {bold('LOCAL'):<28}  {bold('HTTP URL')}")
    print(f"  {'-'*24}  {'-'*26}  {'-'*30}")
    for svc in services:
        lhost   = svc.local_host or "host.docker.internal"
        http    = f"http://{vps}:{svc.remote_port}"
        https   = f"https://{domain}/{svc.name}/" if domain else ""
        url_str = f"{http}  {dim(f'→ {https}') if https else ''}"
        print(f"  {svc.name:<24}  {lhost}:{svc.local_port:<22}  {url_str}")
    print()

def cmd_add(args):
    content  = SERVICES_CONF.read_text(encoding="utf-8")
    services = load_services()
    if any(s.name == args.name for s in services):
        print(f"  {red('✗')}  '{args.name}' already exists.")
        sys.exit(1)
    lhost_part = f" : {args.docker}" if args.docker else ""
    entry = f"{args.name:<16}: {args.local_port:<6}: {args.remote_port}{lhost_part}"
    SERVICES_CONF.write_text(content.rstrip() + f"\n{entry}\n", encoding="utf-8")
    print(f"  {green('✓')}  Added: {bold(entry)}")
    if not getattr(args, "no_sync", False):
        cmd_sync(args)

def cmd_remove(args):
    lines = SERVICES_CONF.read_text(encoding="utf-8").splitlines()
    out, removed = [], False
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and s.split(":")[0].strip() == args.name:
            removed = True
            continue
        out.append(line)
    if not removed:
        print(f"  {red('✗')}  '{args.name}' not found.")
        sys.exit(1)
    SERVICES_CONF.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"  {green('✓')}  Removed: {bold(args.name)}")
    if not getattr(args, "no_sync", False):
        cmd_sync(args)

def cmd_sync(_args):
    print()
    env       = load_config()
    vps_host  = env.get("VPS_HOST",  "")
    frp_token = env.get("FRP_TOKEN", "")
    domain    = env.get("DOMAIN",    "")
    services  = load_services()

    FRPC_INI.write_text(gen_frpc_ini(services, vps_host, frp_token), encoding="utf-8")
    print(f"  {green('✓')}  local/frpc.ini")

    VPS_COMPOSE.write_text(gen_vps_compose(services), encoding="utf-8")
    print(f"  {green('✓')}  vps/docker-compose.yml")

    if vps_host and get_ssh_key().exists():
        scp_file(VPS_COMPOSE, vps_host, "~/porthole/vps/docker-compose.yml")
        ssh_cmd(vps_host, "cd ~/porthole/vps && docker compose up -d --quiet-pull 2>/dev/null")
        print(f"  {green('✓')}  VPS frps restarted")
        if domain:
            scp_str(gen_nginx_conf(domain, services), vps_host, "/etc/nginx/sites-available/porthole")
            ssh_cmd(vps_host, "nginx -t 2>/dev/null && systemctl reload nginx")
            print(f"  {green('✓')}  Nginx config updated")
    else:
        print(f"  {yellow('⚠')}  SSH key or VPS_HOST missing — skipping VPS push")

    sync_firewall(services, extra_ports=[80, 443] if domain else [])

    result = run("docker compose -f local/docker-compose.yml up -d --force-recreate frpc", silent=True)
    print(f"  {green('✓')}  local frpc restarted" if result.returncode == 0
          else f"  {yellow('⚠')}  Docker not running locally — restart frpc manually")

    print(f"\n  {bold('Services')} ({len(services)}):")
    for svc in services:
        lhost = svc.local_host or "host.docker.internal"
        url   = f"https://{domain}/{svc.name}/" if domain else f"http://{vps_host}:{svc.remote_port}"
        print(f"    {svc.name:<20}  {lhost}:{svc.local_port}  →  {url}")
    print()

def cmd_status(_args):
    env      = load_config()
    vps_host = env.get("VPS_HOST", "")
    domain   = env.get("DOMAIN",   "")
    services = load_services()

    if not vps_host:
        print(f"  {red('✗')}  VPS_HOST not set")
        return

    print(f"\n  {bold('Tunnel')}  ({vps_host})\n")
    print(f"  {green('✓') if port_open(vps_host, 7000) else red('✗')}  frps control   :7000")
    for svc in services:
        up = port_open(vps_host, svc.remote_port)
        print(f"  {green('✓') if up else red('✗')}  {svc.name:<20} http://{vps_host}:{svc.remote_port}")

    if domain:
        print(f"\n  {bold('HTTPS')}  ({domain})\n")
        for svc in services:
            ok = https_check(domain, f"/{svc.name}/")
            print(f"  {green('✓') if ok else red('✗')}  {svc.name:<20} https://{domain}/{svc.name}/")
        try:
            import ssl, datetime, socket as _socket
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(_socket.socket(), server_hostname=domain) as s:
                s.settimeout(5)
                s.connect((domain, 443))
                cert    = s.getpeercert()
                expires = datetime.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                days    = (expires - datetime.datetime.utcnow()).days
                icon    = green("✓") if days > 14 else yellow("!")
                print(f"\n  {icon}  SSL cert expires in {bold(str(days))} days ({expires.strftime('%Y-%m-%d')})")
        except Exception:
            print(f"  {yellow('⚠')}  Could not check cert expiry")
    print()

def cmd_secure(args):
    env      = load_config()
    vps_host = env.get("VPS_HOST", "")
    domain   = env.get("DOMAIN",   "")
    email    = env.get("EMAIL",    "")
    services = load_services()

    if args.secure_cmd == "setup":
        if not domain:
            print(f"  {red('✗')}  No domain set. Run: python porthole.py config --domain yourname.duckdns.org")
            sys.exit(1)
        if not email:
            print(f"  {red('✗')}  No email set. Run: python porthole.py config --email you@example.com")
            sys.exit(1)
        if not vps_host or not get_ssh_key().exists():
            print(f"  {red('✗')}  VPS_HOST or SSH key missing.")
            sys.exit(1)

        print(f"\n  Setting up HTTPS for {bold(domain)} on {vps_host}...\n")

        ddns_token = env.get("DUCKDNS_TOKEN", "")
        if ddns_token and "duckdns.org" in domain:
            ok = duckdns_update(domain, vps_host, ddns_token)
            if ok:
                print(f"  {green('✓')}  DuckDNS updated  →  {domain} points to {vps_host}")
            else:
                print(f"  {red('✗')}  DuckDNS update failed — check your DUCKDNS_TOKEN")
                sys.exit(1)
        else:
            print(f"  {yellow('!')}  Make sure {domain} points to {vps_host} before continuing")
            input("     Press Enter when DNS is ready... ")

        sync_firewall(services, extra_ports=[80, 443])
        print(f"  Installing Nginx + Certbot...")
        ssh_cmd(vps_host, "apt-get update -qq && apt-get install -y -qq nginx certbot python3-certbot-nginx")
        print(f"  {green('✓')}  Nginx + Certbot installed")

        pre_conf = (
            f"server {{\n    listen 80;\n    server_name {domain};\n"
            f"    location / {{ return 200 'ok'; add_header Content-Type text/plain; }}\n}}\n"
        )
        scp_str(pre_conf, vps_host, "/etc/nginx/sites-available/porthole")
        ssh_cmd(vps_host, "ln -sf /etc/nginx/sites-available/porthole /etc/nginx/sites-enabled/porthole && nginx -t 2>/dev/null && systemctl reload nginx")
        print(f"  {green('✓')}  Nginx configured")

        print(f"  Requesting SSL certificate from Let's Encrypt...")
        result = ssh_cmd(vps_host, f"certbot certonly --nginx -d {domain} --non-interactive --agree-tos -m {email} 2>&1")
        if result.returncode != 0:
            print(f"  {red('✗')}  Certbot failed. Make sure {domain} points to {vps_host} (port 80 must be reachable).")
            sys.exit(1)
        print(f"  {green('✓')}  SSL certificate issued")

        scp_str(gen_nginx_conf(domain, services), vps_host, "/etc/nginx/sites-available/porthole")
        ssh_cmd(vps_host, "nginx -t 2>/dev/null && systemctl reload nginx")
        print(f"  {green('✓')}  Nginx SSL config applied")

        ssh_cmd(vps_host, "(crontab -l 2>/dev/null | grep -v certbot; echo '0 3 * * * certbot renew --quiet && systemctl reload nginx') | crontab -")
        print(f"  {green('✓')}  Auto-renewal cron set (daily at 3am)")

        print(f"\n  {bold('HTTPS is live!')}  Your services:\n")
        for svc in services:
            print(f"    https://{domain}/{svc.name}/")
        print()

    elif args.secure_cmd == "status":
        cmd_status(None)

    elif args.secure_cmd == "renew":
        if not vps_host or not get_ssh_key().exists():
            print(f"  {red('✗')}  VPS_HOST or SSH key missing.")
            sys.exit(1)
        print(f"  Renewing certificates...")
        ssh_cmd(vps_host, "certbot renew --quiet && systemctl reload nginx")
        print(f"  {green('✓')}  Done. Run 'python porthole.py secure status' to check.")

    else:
        print("  Usage: python porthole.py secure [setup|status|renew]")
