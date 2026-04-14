```
██╗      █████╗ ██████╗     ███████╗███████╗ ██████╗
██║     ██╔══██╗██╔══██╗    ██╔════╝██╔════╝██╔════╝
██║     ███████║██████╔╝    ███████╗█████╗  ██║
██║     ██╔══██║██╔══██╗    ╚════██║██╔══╝  ██║
███████╗██║  ██║██████╔╝    ███████║███████╗╚██████╗
╚══════╝╚═╝  ╚═╝╚═════╝     ╚══════╝╚══════╝ ╚═════╝
```

![Status](https://img.shields.io/badge/status-active-00ff88?style=for-the-badge&labelColor=0d1117)
![Splunk](https://img.shields.io/badge/Splunk-10.2.1-ff6b35?style=for-the-badge&labelColor=0d1117)
![Proxmox](https://img.shields.io/badge/Proxmox-9.1-e57000?style=for-the-badge&labelColor=0d1117)
![Tailscale](https://img.shields.io/badge/Tailscale-connected-4a9eff?style=for-the-badge&labelColor=0d1117)
![Fedora](https://img.shields.io/badge/Fedora-43-51a2da?style=for-the-badge&labelColor=0d1117)

**A hands-on enterprise-grade security lab built from commodity hardware.**  
Attack. Detect. Defend. Repeat.

---

## Hardware

| Device | Specs | Role |
|---|---|---|
| Dell OptiPlex 7010 | i5-3570 @ 3.4GHz · 15.5GB RAM · HDD | Primary hypervisor |
| HP ProLiant DL360 G7 | 2x X5650 Xeon · 32GB RAM · 4x SAS | Remote lab node (Iowa) |
| HP ProBook 650 G8 | i5-11th Gen · 16GB RAM · 475GB NVMe | Dedicated lab terminal |
| Raspberry Pi 5 | 8GB RAM · Vilros kit | DNS + network monitoring |
| TP-Link TL-SG108E | 8-port managed | Lab switching |
| MacBook Air M2 | macOS 13.5 | Management workstation |

---

## Network Architecture

```
Internet
    │
Apartment Router ── cannot access, no port forwarding
    │
    ├── MacBook Air (WiFi) ─────────────── 172.20.x.x
    ├── HP ProBook 650 G8 (WiFi) ────────── 100.74.18.2 (Tailscale)
    └── Dell OptiPlex (Ethernet) ────────── 172.20.16.175
              │
         Proxmox VE 9.1.1
              │
    ┌─────────┼──────────┐
    │         │          │
 OPNsense   Kali      Splunk
 192.168.1.1  .100      .103

HP ProLiant (Iowa) ──── Tailscale: 100.119.210.126
    └── Wazuh (planned)
    └── Active Directory lab (planned)

Raspberry Pi 5 ─────── Tailscale: 100.119.34.79
    └── Pi-hole (DNS)
    └── Zeek (network monitoring)

─────────────────────────────────────────────────
Tailscale Overlay (bypasses apartment NAT)
─────────────────────────────────────────────────
MacBook      100.104.62.66
Kali         100.77.251.92
Proxmox      100.90.195.73
Pi           100.119.34.79
Splunk       100.81.37.2
ProLiant     100.119.210.126
Fedora       100.74.18.2
```

---

## Stack

### OptiPlex — Local Lab Node

**Proxmox VE 9.1.1** — Hypervisor running all local VMs. Kali, OPNsense, and Splunk live here.

**OPNsense** (VM 200) — Virtual firewall and router. Handles all routing, NAT, DHCP, and DNS forwarding for the `192.168.1.x` lab subnet. Unbound forwards DNS queries to Pi-hole.

**Kali Linux** (VM 100) — Attack platform. Runs exploits, enumeration tools, and offensive payloads against lab targets. Splunk Universal Forwarder installed and shipping 40,000+ events.

**Splunk Enterprise 10.2.1** (VM 101) — SIEM. Ingesting logs from Kali via Universal Forwarder on port 9997. Next: ingest Wazuh alerts from the ProLiant.

---

### ProLiant — Remote Heavy-Lift Node

**Wazuh 4.x** *(in progress)* — Full stack: manager, indexer, dashboard. Moved here from the OptiPlex after HDD timeouts killed OpenSearch initialization repeatedly. 32GB RAM and SAS drives handle it properly.

**Active Directory Lab** *(planned)* — Windows Server 2022 domain controller + domain-joined Windows 10/11 victim VMs. BloodHound enumeration, Kerberoasting, Pass-the-Hash, DCSync attacks from Kali — detection in Wazuh and Splunk.

---

### HP ProBook 650 G8 — Dedicated Lab Terminal

Fresh Fedora 43 install with full attack tooling, remote access, and SIEM forwarding. This is the primary workstation for operating the lab.

**OS:** Fedora 43 Workstation, LUKS full-disk encryption  
**Shell:** zsh + Oh My Zsh + Powerlevel10k  
**Remote access:** Tailscale (`100.74.18.2`), SSH key auth to all nodes  

#### Tools Installed

| Tool | Purpose |
|---|---|
| Metasploit 6.4 | Exploitation framework |
| Burp Suite Community | Web app proxy / interceptor |
| gobuster | Directory and DNS fuzzing |
| ffuf | Fast web fuzzer |
| hydra | Password brute-force |
| nikto | Web server scanner |
| nmap | Network/port scanning |
| wireshark | Packet capture and analysis |
| tcpdump | CLI packet capture |
| SecLists | Wordlist collection (~1GB) |
| sqlmap | SQL injection automation |
| ansible | Node management / automation |
| auditd | Local system audit logging |
| fail2ban | Brute-force protection |
| Splunk UF 10.2.2 | Forwarding logs to Splunk SIEM |

---

### Raspberry Pi 5 — Perimeter Node

**Pi-hole** — Network-level DNS sinkhole. All lab DNS routes through it.

**Zeek 8.1.1** — Passive network monitoring on `eth0`. Generates structured logs for connections, DNS, HTTP, SSL, and file transfers.

**Tailscale** — Enrolled on all lab nodes. Bypasses apartment NAT via outbound-only connections.

---

## Tool Usage Reference

### SSH — Connecting to Lab Nodes

SSH config is set up with named hosts. From the ProBook terminal:

```bash
ssh proxmox     # Proxmox hypervisor (OptiPlex)
ssh proliant    # ProLiant remote node (Iowa)
ssh pi          # Raspberry Pi 5
ssh kali        # Kali Linux VM
ssh splunk      # Splunk VM
```

All connections go over Tailscale IPs. No VPN setup required, just needs Tailscale running (`tailscale status` to verify).

---

### tmux — Terminal Multiplexer

tmux keeps sessions alive and lets you split the terminal into panes. Essential for monitoring multiple things at once.

```bash
tmux                  # start a new session
tmux attach           # reattach to existing session
tmuxinator start lab  # launch full lab layout (local + proxmox + pi + logs)
```

**Key bindings** (prefix is `Ctrl+a`):

| Keys | Action |
|---|---|
| `Ctrl+a \|` | Split pane vertically |
| `Ctrl+a -` | Split pane horizontally |
| `Ctrl+a z` | Zoom current pane fullscreen |
| `Ctrl+a d` | Detach session (keeps it running) |
| `Ctrl+a [0-9]` | Switch windows |
| Click | Move between panes (mouse enabled) |

---

### Metasploit — Exploitation Framework

```bash
msfconsole           # launch Metasploit
```

Basic workflow inside msfconsole:

```
search <exploit name>          # find a module
use <module path>              # load a module
show options                   # see required params
set RHOSTS <target IP>         # set target
set LHOST <your IP>            # set listener
run                            # execute
```

Example — run a scan:
```
use auxiliary/scanner/portscan/tcp
set RHOSTS 192.168.1.0/24
run
```

---

### Nmap — Network Scanning

```bash
# Quick scan
nmap 192.168.1.0/24

# Full port scan with service detection
nmap -sV -p- 192.168.1.100

# OS detection + scripts
nmap -A 192.168.1.100

# Scan through Tailscale
nmap 100.90.195.73
```

---

### Gobuster — Directory Fuzzing

```bash
# Directory brute force
gobuster dir -u http://target.com -w ~/tools/SecLists/Discovery/Web-Content/common.txt

# DNS subdomain enumeration
gobuster dns -d target.com -w ~/tools/SecLists/Discovery/DNS/subdomains-top1million-5000.txt
```

---

### ffuf — Fast Web Fuzzer

```bash
# Directory fuzzing
ffuf -u http://target.com/FUZZ -w ~/tools/SecLists/Discovery/Web-Content/common.txt

# Parameter fuzzing
ffuf -u http://target.com/page?param=FUZZ -w ~/tools/SecLists/Fuzzing/special-chars.txt

# Filter by status code
ffuf -u http://target.com/FUZZ -w wordlist.txt -fc 404
```

---

### Hydra — Password Brute Force

```bash
# SSH brute force
hydra -l admin -P ~/tools/SecLists/Passwords/Common-Credentials/10k-most-common.txt ssh://192.168.1.100

# HTTP login form
hydra -l admin -P passwords.txt 192.168.1.100 http-post-form "/login:user=^USER^&pass=^PASS^:Invalid"

# FTP
hydra -l admin -P passwords.txt ftp://192.168.1.100
```

---

### Nikto — Web Server Scanner

```bash
# Basic scan
nikto -h http://192.168.1.100

# Scan specific port
nikto -h http://192.168.1.100 -p 8080

# Output to file
nikto -h http://192.168.1.100 -o scan_results.txt
```

---

### Ansible — Node Management

Inventory lives at `~/lab/ansible/inventory`. Manage all lab nodes from one place.

```bash
# Ping all nodes
ansible all -i ~/lab/ansible/inventory -m ping --private-key ~/.ssh/id_ed25519

# Run a command on all nodes
ansible all -i ~/lab/ansible/inventory -a "uptime" --private-key ~/.ssh/id_ed25519

# Run on a specific group
ansible proxmox -i ~/lab/ansible/inventory -a "df -h" --private-key ~/.ssh/id_ed25519

# Run a playbook
ansible-playbook -i ~/lab/ansible/inventory ~/lab/ansible/ping.yml
```

Node groups: `proxmox`, `pi`, `proliant`, `lab` (all of them)

---

### Splunk Universal Forwarder — Log Shipping

The ProBook ships its `/var/log` to Splunk at `100.81.37.2:9997`. The forwarder runs as a systemd service.

```bash
# Check status
sudo systemctl status SplunkForwarder

# Restart
sudo systemctl restart SplunkForwarder

# Add a new log source
sudo /opt/splunkforwarder/bin/splunk add monitor /path/to/logs

# View forwarding config
sudo /opt/splunkforwarder/bin/splunk list forward-server
```

---

### Push SSH Keys to New Nodes

When spinning up a new VM or node:

```bash
~/lab/push-keys.sh
```

This pushes your public key to all configured lab nodes in one shot. Edit the script to add new hosts.

---

### Neovim

```bash
nvim <file>     # open a file
nvim .          # open directory browser
```

Key plugins installed: Telescope (fuzzy file finder), NERDTree (file tree), vim-airline (status bar), Treesitter (syntax), LSP (language server).

```
:NERDTree           # open file tree
:Telescope find_files  # fuzzy find files
:PlugUpdate         # update plugins
```

---

## What's Running

```
elijah@splunk:~$ splunk search "index=* host=kali" | stats count
41,949 events indexed from Kali Linux
Sources: /var/log/* (dpkg, auth, syslog, lightdm, apt)
Pipeline: Kali → Universal Forwarder → Splunk:9997 → indexed

Fedora ProBook → Universal Forwarder → Splunk:9997 → queued (Splunk offline)
```

---

## Lessons Learned (the hard way)

**Memory ballooning will starve your VMs.** Proxmox's balloon driver dynamically restricts RAM. OpenSearch, Splunk, and any Java-based workload needs full allocation at startup — disable ballooning.

**HDDs and OpenSearch don't mix.** First-time index initialization on a spinning disk is too slow. The Wazuh installer's hardcoded timeout fires before OpenSearch becomes healthy. SSD or bust.

**OPNsense and pfSense dropped ARM64.** The Pi cannot run either. Hypervisor VM is the correct approach for the firewall role.

**Apartment NAT kills WireGuard.** Inbound UDP is blocked at the upstream router. Tailscale uses outbound-only connections and punches through NAT without port forwarding. Use it from the start.

**Live USB installs nothing.** Fedora's live environment is a RAM-based OS — nothing persists on reboot. Always install to disk before configuring anything.

**Wildcard RPM installs will pick up broken files.** A failed `curl` that saves an XML error as a `.rpm` will break `rpm -i *.rpm`. Always check what's in the directory before installing.

**Document every failure.** Eight documented Wazuh install failures before pivoting to better hardware. Each one is a lesson that sticks.

---

## Roadmap

- [x] Proxmox VE hypervisor
- [x] OPNsense virtual firewall
- [x] Kali Linux attack VM
- [x] Pi-hole DNS filtering
- [x] Zeek network monitoring
- [x] Tailscale remote access
- [x] Splunk Enterprise SIEM
- [x] Universal Forwarder on Kali
- [x] Dedicated lab terminal (HP ProBook 650 G8 / Fedora 43)
- [x] Full attack tooling (Metasploit, Burp, gobuster, ffuf, hydra, nikto)
- [x] Ansible lab automation
- [x] Splunk UF on ProBook
- [ ] Wazuh on ProLiant (in progress)
- [ ] Windows Server 2022 AD lab
- [ ] BloodHound enumeration scenarios
- [ ] Attack/detect scenarios (Kerberoasting, Pass-the-Hash, DCSync)
- [ ] Wazuh → Splunk alert forwarding
- [ ] AWS/Azure integration
- [ ] Rubber Ducky payload lab

---

## Access Reference

| System | Address |
|---|---|
| Proxmox (local) | `https://100.90.195.73:8006` |
| Proxmox (remote) | `https://100.119.210.126:8006` |
| Splunk Web | `http://100.81.37.2:8000` |
| OPNsense | `https://192.168.1.1` |
| Pi SSH | `ssh pi` |
| Kali SSH | `ssh kali` |
| Splunk SSH | `ssh splunk` |
| Proxmox SSH | `ssh proxmox` |
| ProLiant SSH | `ssh proliant` |

---

**B.S. Cybersecurity (in progress) · CompTIA Security+ · Microsoft AZ-900**

*Certs teach you concepts. Labs teach you how things actually break.*
