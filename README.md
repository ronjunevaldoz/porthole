<div align="center">

# 🕳️ Porthole

**Expose your local AI models and servers to the internet — no router config needed.**

Tunnels any local service (Ollama, Ktor, FastAPI, …) through a cheap VPS using [FRP](https://github.com/fatedier/frp).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-required-blue?logo=docker)
![FRP](https://img.shields.io/badge/FRP-v0.51.3-orange)

</div>

---

## How it works

```
Your Machine                  VPS (DigitalOcean, etc.)          Internet
──────────────────────────    ──────────────────────────────    ──────────
ollama  :11434                frps listens on :7000
ktor    :8080    ──frpc──►    exposes all tunnels           ◄── any client
fastapi :8000                 on their configured ports
```

The tunnel is initiated **outbound** from your machine — no port forwarding or router changes needed.

---

## Requirements

| Where | What |
|---|---|
| Your machine | Python 3.8+, Docker |
| VPS | Docker, Ubuntu (any cloud provider) |

---

## Quick start

### 1 — Clone

```bash
git clone https://github.com/ronjunevaldoz/porthole.git
cd porthole
```

### 2 — Configure

```bash
python porthole.py config --vps <YOUR_VPS_IP>
python porthole.py config --token <YOUR_FRP_TOKEN>   # or use --rotate-token to auto-generate
python porthole.py config --dashboard <PASSWORD>
```

> **First time?** Generate a token with `openssl rand -hex 32`  
> or let porthole do it: `python porthole.py config --rotate-token`

### 3 — Add your services

```bash
python porthole.py add ollama  11434 11434   # native Ollama
python porthole.py add ktor    8080  8080    # native Ktor
python porthole.py add fastapi 8000  8000    # native FastAPI
```

Each `add` automatically syncs everything — configs, VPS, and firewall.

### 4 — Check status

```bash
python porthole.py status
#  ✓  frps control   :7000
#  ✓  ollama         http://<VPS_IP>:11434
#  ✓  ktor           http://<VPS_IP>:8080
#  ✓  fastapi        http://<VPS_IP>:8000
```

---

## CLI reference

```bash
python porthole.py config                       # show current VPS/token config
python porthole.py config --vps <IP>            # set VPS host
python porthole.py config --token <TOKEN>       # set FRP token
python porthole.py config --dashboard <PWD>     # set dashboard password
python porthole.py config --rotate-token        # generate a new token automatically

python porthole.py list                         # list configured services
python porthole.py add <name> <lport> <rport>   # add a service and sync
python porthole.py add mydb 5432 5432 --docker postgres  # docker service
python porthole.py remove <name>                # remove a service and sync
python porthole.py sync                         # force sync everything
python porthole.py status                       # check tunnel health
```

---

## Service types

| Service runs as | `--docker` flag | Example |
|---|---|---|
| Native process on your machine | *(omit)* | `python porthole.py add ktor 8080 8080` |
| Docker container (same compose) | `--docker <name>` | `python porthole.py add ollama 11434 11434 --docker ollama` |

> Native services must bind to `0.0.0.0`, not `127.0.0.1`.

---

## Server examples

### Ollama (native)
```bash
# Set OLLAMA_HOST before starting
OLLAMA_HOST=0.0.0.0 ollama serve          # macOS/Linux
# Windows: set OLLAMA_HOST=0.0.0.0 as a system environment variable

python porthole.py add ollama 11434 11434
```

### Ktor
Bind to `0.0.0.0` in `application.conf`:
```hocon
ktor {
    deployment {
        port = 8080
        host = 0.0.0.0
    }
}
```
```bash
python porthole.py add ktor 8080 8080
```

### FastAPI
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
python porthole.py add fastapi 8000 8000
```

---

## VPS setup (DigitalOcean)

The quickest path:

```bash
# Install doctl and authenticate
doctl auth init

# Create a $4/mo droplet (Singapore)
doctl compute droplet create porthole-vps \
  --region sgp1 --image ubuntu-24-04-x64 --size s-1vcpu-512mb-10gb \
  --ssh-keys <your-key-id> --tag-names porthole --wait \
  --user-data '#!/bin/bash
curl -fsSL https://get.docker.com | sh'

# Create firewall (porthole CLI manages ports automatically after this)
doctl compute firewall create \
  --name porthole-fw --tag-names porthole \
  --inbound-rules "protocol:tcp,ports:22,address:0.0.0.0/0 protocol:tcp,ports:7000,address:0.0.0.0/0 protocol:tcp,ports:7500,address:0.0.0.0/0" \
  --outbound-rules "protocol:tcp,ports:all,address:0.0.0.0/0 protocol:udp,ports:all,address:0.0.0.0/0"
```

Then deploy frps:
```bash
ssh root@<VPS_IP> "mkdir -p ~/porthole/vps"
scp -r vps/ root@<VPS_IP>:~/porthole/
ssh root@<VPS_IP> "cd ~/porthole/vps && docker compose up -d"
```

---

## Dashboard

`http://<VPS_IP>:7500` — login `admin` / your dashboard password to monitor live tunnels.

---

## Security notes

- Traffic through the tunnel is **not TLS-encrypted** by default.  
  For production, put Nginx + Certbot in front of your ports on the VPS.
- Never commit `.env` files — `.gitignore` already excludes them.
- Rotate your token anytime: `python porthole.py config --rotate-token && python porthole.py sync`

---

## License

MIT
