```text
██╗      █████╗ ██████╗     ███████╗███████╗ ██████╗
██║     ██╔══██╗██╔══██╗    ██╔════╝██╔════╝██╔════╝
██║     ███████║██████╔╝    ███████╗█████╗  ██║
██║     ██╔══██║██╔══██╗    ╚════██║██╔══╝  ██║
███████╗██║  ██║██████╔╝    ███████║███████╗╚██████╗
╚══════╝╚═╝  ╚═╝╚═════╝     ╚══════╝╚══════╝ ╚═════╝
```text

**Attack. Detect. Defend. Repeat.**

![Status](https://img.shields.io/badge/STATUS-ACTIVE-00ff88?style=for-the-badge&labelColor=0a0a0a&color=00ff88)
![Proxmox](https://img.shields.io/badge/PROXMOX-9.1-e57000?style=for-the-badge&labelColor=0a0a0a)
![Splunk](https://img.shields.io/badge/SPLUNK-10.2.1-ff6b35?style=for-the-badge&labelColor=0a0a0a)
![Fedora](https://img.shields.io/badge/FEDORA-43-51a2da?style=for-the-badge&labelColor=0a0a0a)
![Tailscale](https://img.shields.io/badge/TAILSCALE-MESH-4a9eff?style=for-the-badge&labelColor=0a0a0a)
![Wazuh](https://img.shields.io/badge/WAZUH-IN_PROGRESS-ffcc00?style=for-the-badge&labelColor=0a0a0a)

*A hands-on enterprise-grade security lab built from commodity hardware.*  
*Real attacks. Real detections. Real skill.*

---

## ⚡ What This Is

This is not a homelab for running Plex. This is a full-spectrum offensive and defensive security environment built to simulate enterprise attack scenarios, develop real detection engineering skills, and prepare for a career in cybersecurity. Every component was chosen, configured, and broken at least twice.

Built on a mix of repurposed enterprise hardware and consumer gear — because that's what real labs look like.

---

## 🖥️ Hardware

| Device | Specs | Role |
|---|---|---|
| **Dell OptiPlex 7010** | i5-3570 · 15.5GB RAM · HDD | Primary hypervisor (Proxmox) |
| **HP ProLiant DL360 G7** | 2× Xeon X5650 · 32GB RAM · SAS | Remote heavy-lift node (Iowa) |
| **HP ProBook 650 G8** | i7-1165G7 · 16GB RAM · 475GB NVMe | Dedicated attack terminal (Fedora 43) |
| **Raspberry Pi 5** | 8GB RAM | DNS sinkhole + network monitoring |
| **TP-Link TL-SG108E** | 8-port managed switch | Lab switching |
| **MacBook Air M2** | macOS 13.5 | Secondary management workstation |

---

## 🌐 Network Architecture

```text
                        INTERNET
                            │
              Apartment Router (172.20.x.x)
              ⚠️  No port forwarding — NAT blocked
                            │
                ┌───────────┴───────────┐
                │                       │
         OptiPlex (Ethernet)      ProBook (WiFi)
         172.20.16.175            Tailscale: 100.74.18.2
                │
         Proxmox VE 9.1.1
                │
     ┌──────────┼──────────┐
     │          │          │
  OPNsense    Kali       Splunk
  192.168.1.1  .100       .103
  (VM 200)   (VM 100)   (VM 101)

  Iowa ──────────────────────────────────────
  HP ProLiant DL360 G7
  Tailscale: 100.119.210.126
  └── Wazuh (deploying)
  └── Windows Server 2022 AD (planned)
  └── BloodHound lab (planned)

  Tampa ─────────────────────────────────────
  Raspberry Pi 5
  Tailscale: 100.119.34.79
  └── Pi-hole DNS
  └── Zeek 8.1.1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TAILSCALE MESH (bypasses apartment NAT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  fedora        100.74.18.2
  macbook       100.104.62.66
  kali          100.77.251.92
  proxmox       100.90.195.73
  splunk        100.81.37.2
  raspberrypi   100.119.34.79
  proliant      100.119.210.126
```text

---

## 🏗️ Stack

### 🔴 OptiPlex — Local Hypervisor

**Proxmox VE 9.1.1** — Bare metal hypervisor. Hosts all local VMs. Type 1 hypervisor on repurposed desktop hardware.

**OPNsense** `VM 200 · 192.168.1.1` — Virtual firewall and router. Full NAT, DHCP, DNS forwarding via Unbound → Pi-hole. Segments the lab subnet from the apartment network.

**Kali Linux** `VM 100 · 192.168.1.100` — Primary attack platform. Full offensive toolkit. Splunk Universal Forwarder installed, shipping 40,000+ events to SIEM.

**Splunk Enterprise 10.2.1** `VM 101 · 192.168.1.103` — SIEM. Ingesting logs from Kali and the ProBook via Universal Forwarder on port 9997.

---

### 🟠 ProLiant — Remote Heavy-Lift Node

Dual-socket Xeon server co-located in Iowa. Accessed exclusively via Tailscale.

**Wazuh** *(deploying)* — Full stack HIDS: manager + OpenSearch indexer + dashboard. Previously failed on OptiPlex due to spinning HDD I/O timeouts killing OpenSearch initialization. The ProLiant's SAS drives and 32GB RAM handle it properly.

**Windows Server 2022 AD Lab** *(planned)* — Domain controller + Windows 10/11 victim VMs. Attack scenarios:
- BloodHound enumeration
- Kerberoasting
- Pass-the-Hash
- DCSync
- Detection in Wazuh + Splunk

---

### 🟡 ProBook 650 G8 — Attack Terminal

Fresh Fedora 43 install. Full-disk LUKS encryption. This is the daily driver for operating the lab.

**OS:** Fedora 43 · LUKS encrypted · i7-1165G7 · 16GB RAM · 475GB NVMe  
**Shell:** zsh + Oh My Zsh + Powerlevel10k + autosuggestions + syntax highlighting  
**Terminal multiplexer:** tmux with custom keybindings and status bar  
**Editor:** Neovim with LSP, Treesitter, Telescope, Catppuccin  

#### Attack Tooling

| Tool | Purpose |
|---|---|
| Metasploit 6.4 | Exploitation framework |
| Burp Suite Community | Web app proxy / interceptor |
| gobuster | Directory and DNS fuzzing |
| ffuf | Fast web fuzzer |
| hydra | Credential brute-force |
| nikto | Web server scanning |
| nmap | Network reconnaissance |
| wireshark | Packet capture and analysis |
| tcpdump | CLI packet capture |
| sqlmap | SQL injection automation |
| SecLists | Wordlist collection (~1GB) |

#### Infrastructure & Automation

| Tool | Purpose |
|---|---|
| Ansible | Node management and automation |
| Tailscale | Mesh VPN — zero config remote access |
| Splunk UF 10.2.2 | Forwarding local logs to SIEM |
| auditd | Local system audit logging |
| fail2ban | Brute-force protection |
| rkhunter | Rootkit scanning (498 checks, 0 found) |
| ClamAV | Malware scanning |
| virt-manager | Local VM management |
| Remmina | Remote desktop client (RDP/VNC/SSH) |
| Claude Code | AI-assisted development in terminal |
| Obsidian | Lab notes, CTF writeups, attack playbooks |

---

### 🟢 Raspberry Pi 5 — Perimeter Node

**Pi-hole** — Network DNS sinkhole. Every lab DNS query flows through it. Malware C2 beaconing shows up here before anything else catches it.

**Zeek 8.1.1** — Passive network traffic analysis on `eth0`. Structured logs for connections, DNS, HTTP, SSL, and file transfers. Deployed outside the OPNsense perimeter for an independent vantage point.

---

## 🛠️ Tool Usage Reference

### SSH — One-Command Node Access

```bash
ssh proxmox     # OptiPlex hypervisor
ssh proliant    # Iowa ProLiant
ssh pi          # Raspberry Pi 5
ssh kali        # Kali attack VM
ssh splunk      # Splunk SIEM VM
```text

All connections route over Tailscale. Passwordless via ED25519 key auth.

---

### tmux — Session Management

Prefix key: `Ctrl+a`

| Binding | Action |
|---|---|
| `Ctrl+a \|` | Split vertical |
| `Ctrl+a -` | Split horizontal |
| `Ctrl+a z` | Zoom pane fullscreen |
| `Ctrl+a d` | Detach session |
| Mouse click | Switch panes |

```bash
tmuxinator start lab    # Launch full lab layout
                        # windows: local · proxmox · pi · logs
```text

---

### Metasploit

```bash
msfconsole

# Inside msf:
search <module>
use <path>
show options
set RHOSTS <target>
set LHOST <your IP>
run
```text

---

### Recon Workflow

```bash
# Network discovery
nmap -sV -p- 192.168.1.0/24

# Web directory fuzzing
gobuster dir -u http://target -w ~/tools/SecLists/Discovery/Web-Content/common.txt
ffuf -u http://target/FUZZ -w ~/tools/SecLists/Discovery/Web-Content/common.txt -fc 404

# Credential attacks
hydra -l admin -P ~/tools/SecLists/Passwords/Common-Credentials/10k-most-common.txt ssh://target

# Web scanning
nikto -h http://target
```text

---

### Ansible — Lab Automation

```bash
# Ping all nodes
ansible all -i ~/lab/ansible/inventory -m ping --private-key ~/.ssh/id_ed25519

# Run command on all nodes
ansible all -i ~/lab/ansible/inventory -a "uptime"

# Run on specific group
ansible proxmox -i ~/lab/ansible/inventory -a "df -h"
```text

Node groups: `proxmox` · `pi` · `proliant` · `lab` (all)

---

### Splunk Forwarder

```bash
sudo systemctl status SplunkForwarder
sudo /opt/splunkforwarder/bin/splunk add monitor /path/to/logs
sudo /opt/splunkforwarder/bin/splunk list forward-server
```text

Pipeline: `ProBook /var/log → UF → Splunk:9997 → indexed`

---

### Push SSH Keys to New Nodes

```bash
~/lab/push-keys.sh
```text

Pushes your public key to all configured lab nodes in one shot.

---

## 📊 Current Telemetry

```text
index=* host=kali     → 41,949 events
index=* host=fedora   → queued (Splunk offline)

Sources: auth · syslog · dpkg · apt · lightdm
Pipeline: Universal Forwarder → Splunk Enterprise → indexed
```text

---

## 💀 Lessons Learned (The Hard Way)

**Spinning HDDs will kill OpenSearch.** The Wazuh installer has hardcoded initialization timeouts. On a spinning disk, OpenSearch never becomes healthy in time. Eight documented failure modes before accepting this. SSD is a non-negotiable prerequisite.

**Memory ballooning starves Java workloads.** Proxmox's balloon driver dynamically restricts VM RAM. OpenSearch and Splunk need their full allocation at startup — disable ballooning or watch them OOM silently.

**Apartment NAT kills WireGuard.** Inbound UDP is blocked at the upstream router. Tailscale punches through via outbound-only connections. Use it from day one — don't waste time on WireGuard in a NAT'd environment.

**OPNsense and pfSense dropped ARM64.** The Pi can't run either. Run the firewall as a Proxmox VM instead — better performance, easier snapshots, correct architecture.

**You can't configure a live USB.** Fedora's live environment is a RAM-based OS. Nothing persists on reboot. Install to disk before touching anything.

**Wildcard installs will bite you.** A failed `curl` that saves an XML error page as `.rpm` will silently break `rpm -i *.rpm`. Always verify what's in the directory before installing.

**Never type passwords into a chat window.** Just don't.

**Document every failure.** Each one is a lesson that compounds.

---

## 🗺️ Roadmap

- [x] Proxmox VE hypervisor
- [x] OPNsense virtual firewall
- [x] Kali Linux attack VM
- [x] Pi-hole DNS filtering
- [x] Zeek 8.1.1 network monitoring
- [x] Tailscale mesh VPN
- [x] Splunk Enterprise SIEM
- [x] Universal Forwarder — Kali → Splunk
- [x] HP ProBook 650 G8 attack terminal (Fedora 43)
- [x] Full offensive toolkit (Metasploit · Burp · gobuster · ffuf · hydra · nikto)
- [x] Ansible lab automation
- [x] Universal Forwarder — ProBook → Splunk
- [x] Dotfiles repo
- [ ] **Wazuh full stack on ProLiant** ← next
- [ ] Windows Server 2022 Active Directory lab
- [ ] BloodHound enumeration
- [ ] Kerberoasting / Pass-the-Hash / DCSync scenarios
- [ ] Wazuh → Splunk alert forwarding
- [ ] CTF writeups in Obsidian
- [ ] Rubber Ducky payload lab
- [ ] AWS/Azure cloud integration

---

## 🔗 Access Reference

| System | Address | Protocol |
|---|---|---|
| Proxmox Web UI | `https://100.90.195.73:8006` | HTTPS |
| ProLiant Web UI | `https://100.119.210.126:8006` | HTTPS |
| Splunk Web | `http://100.81.37.2:8000` | HTTP |
| OPNsense | `https://192.168.1.1` | HTTPS |
| Pi-hole | `http://100.119.34.79/admin` | HTTP |
| Proxmox SSH | `ssh proxmox` | SSH/Tailscale |
| Pi SSH | `ssh pi` | SSH/Tailscale |
| Kali SSH | `ssh kali` | SSH/Tailscale |
| Splunk SSH | `ssh splunk` | SSH/Tailscale |
| ProLiant SSH | `ssh proliant` | SSH/Tailscale |

---

**B.S. Cybersecurity** *(in progress)* · **CompTIA Security+** · **Microsoft AZ-900**

*Certs teach you concepts. Labs teach you how things actually break.*
