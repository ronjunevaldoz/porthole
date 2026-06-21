#!/usr/bin/env python3
"""
porthole - manage FRP tunnel services

Usage:
  python porthole.py config                        # show current config
  python porthole.py config --vps IP               # set VPS host
  python porthole.py config --token TOKEN          # set FRP token
  python porthole.py config --dashboard PWD        # set dashboard password
  python porthole.py config --domain DOMAIN        # set domain for HTTPS
  python porthole.py config --email EMAIL          # set email for Let's Encrypt
  python porthole.py config --rotate-token         # generate a new token automatically

  python porthole.py list                          # list services
  python porthole.py add <name> <lport> <rport>   # add service and sync
  python porthole.py remove <name>                 # remove service and sync
  python porthole.py sync                          # sync everything to VPS
  python porthole.py status                        # check tunnel health

  python porthole.py secure setup                  # install Nginx + SSL on VPS
  python porthole.py secure status                 # check HTTPS + cert expiry
  python porthole.py secure renew                  # force cert renewal

  python porthole.py ui                            # open local web dashboard
  python porthole.py ui --port 8888                # use custom port
"""

import argparse

from lib.commands import (
    cmd_config, cmd_list, cmd_add, cmd_remove,
    cmd_sync, cmd_status, cmd_secure,
)
from lib.ui.server import cmd_ui


def main():
    p = argparse.ArgumentParser(
        prog="porthole",
        description="Manage FRP tunnel services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python porthole.py config --vps 1.2.3.4 --domain me.duckdns.org --email me@x.com\n"
            "  python porthole.py add ollama 11434 11434\n"
            "  python porthole.py add ktor 8080 8080\n"
            "  python porthole.py secure setup\n"
            "  python porthole.py status\n"
            "  python porthole.py ui\n"
        ),
    )
    sub = p.add_subparsers(dest="cmd", metavar="command")

    # config
    pc = sub.add_parser("config", help="Show or update config")
    pc.add_argument("--vps",           metavar="IP",     help="Set VPS host")
    pc.add_argument("--token",         metavar="TOKEN",  help="Set FRP token")
    pc.add_argument("--dashboard",     metavar="PWD",    help="Set dashboard password")
    pc.add_argument("--domain",        metavar="DOMAIN", help="Set domain for HTTPS")
    pc.add_argument("--email",         metavar="EMAIL",  help="Set email for Let's Encrypt")
    pc.add_argument("--ssh-key",       metavar="PATH",   help="Set path to SSH private key")
    pc.add_argument("--duckdns-token", metavar="TOKEN",  help="Set DuckDNS token for auto DNS update")
    pc.add_argument("--cors-origin",   metavar="ORIGIN", help="Set CORS origin for Nginx (e.g. https://myapp.netlify.app)")
    pc.add_argument("--rotate-token",  action="store_true", help="Generate a new random token")

    # list / sync / status
    sub.add_parser("list",   help="List services")
    sub.add_parser("sync",   help="Sync configs, push to VPS, update firewall")
    sub.add_parser("status", help="Check tunnel + HTTPS health")

    # add
    pa = sub.add_parser("add", help="Add a service and sync")
    pa.add_argument("name")
    pa.add_argument("local_port",  type=int)
    pa.add_argument("remote_port", type=int)
    pa.add_argument("--docker",  metavar="CONTAINER", help="Docker service name")
    pa.add_argument("--no-sync", action="store_true")

    # remove
    pr = sub.add_parser("remove", help="Remove a service and sync")
    pr.add_argument("name")
    pr.add_argument("--no-sync", action="store_true")

    # secure
    ps = sub.add_parser("secure", help="HTTPS setup via Nginx + Let's Encrypt")
    ps.add_argument("secure_cmd", choices=["setup", "status", "renew"],
                    metavar="[setup|status|renew]")

    # ui
    pu = sub.add_parser("ui", help="Open local web dashboard")
    pu.add_argument("--port", type=int, default=7502, metavar="PORT",
                    help="Local port for the UI server (default: 7502)")

    args = p.parse_args()
    dispatch = {
        "config": cmd_config, "list":   cmd_list,   "add":    cmd_add,
        "remove": cmd_remove, "sync":   cmd_sync,   "status": cmd_status,
        "secure": cmd_secure, "ui":     cmd_ui,
    }
    fn = dispatch.get(args.cmd)
    fn(args) if fn else p.print_help()


if __name__ == "__main__":
    main()
