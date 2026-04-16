<div align="center">

```
██╗      █████╗ ██████╗     ███████╗███████╗ ██████╗
██║     ██╔══██╗██╔══██╗    ██╔════╝██╔════╝██╔════╝
██║     ███████║██████╔╝    ███████╗█████╗  ██║
██║     ██╔══██║██╔══██╗    ╚════██║██╔══╝  ██║
███████╗██║  ██║██████╔╝    ███████║███████╗╚██████╗
╚══════╝╚═╝  ╚═╝╚═════╝     ╚══════╝╚══════╝ ╚═════╝
```

![Status](https://img.shields.io/badge/status-active-00ff88?style=for-the-badge&labelColor=0d1117)
![Proxmox](https://img.shields.io/badge/Proxmox-9.1.1-e57000?style=for-the-badge&labelColor=0d1117)
![Splunk](https://img.shields.io/badge/Splunk-10.2.1-ff6b35?style=for-the-badge&labelColor=0d1117)
![Tailscale](https://img.shields.io/badge/Tailscale-connected-4a9eff?style=for-the-badge&labelColor=0d1117)
![Fedora](https://img.shields.io/badge/Fedora-43-51a2da?style=for-the-badge&labelColor=0d1117)
![Wazuh](https://img.shields.io/badge/Wazuh-4.14-005571?style=for-the-badge&labelColor=0d1117)

**A full-spectrum offensive and defensive security lab built from commodity hardware.**

*Real attacks. Real detections. Real skill.*

</div>

---

## What This Is

This is not a homelab for running Plex or replacing Google Drive. This is an enterprise-grade security operations environment built to simulate real attack scenarios, develop detection engineering skills, and build a portfolio for a career in cybersecurity.

Every component was deliberately chosen, manually configured, and broken at least twice before it worked. That's the point.

Built across three physical locations on repurposed enterprise hardware and consumer gear — because that's what real labs look like.

---

## Table of Contents

- [Hardware](#hardware)
- [Network Architecture](#network-architecture)
- [Infrastructure Stack](#infrastructure-stack)
  - [OptiPlex — Local Hypervisor](#optiplex--local-hypervisor)
  - [ProLiant — Remote Heavy-Lift Node](#proliant--remote-heavy-lift-node)
  - [Raspberry Pi 5 — Perimeter Node](#raspberry-pi-5--perimeter-node)
  - [ProBook 650 G8 — Attack Terminal](#probook-650-g8--attack-terminal)
- [Access Reference](#access-reference)
- [Tool Reference](#tool-reference)
- [Lessons Learned](#lessons-learned)
- [Roadmap](#roadmap)

---

## Hardware

| Device | Specs | Role | Location |
|---|---|---|---|
| **Dell OptiPlex 7010** | i5-3570 @ 3.4GHz · 15.5GB RAM · HDD | Primary hypervisor (Proxmox) | Tampa apartment |
| **HP ProLiant DL360 G7** | 2x Xeon X5650 · 32GB RAM · 4x SAS | Remote heavy-lift node | Iowa (co-located) |
| **HP ProBook 650 G8** | i7-1165G7 · 16GB RAM · 475GB NVMe | Dedicated attack terminal | Tampa (daily driver) |
| **Raspberry Pi 5** | BCM2712 · 8GB RAM · Vilros kit | DNS sinkhole + network monitoring | Tampa apartment |
| **TP-Link TL-SG108E** | 8-port managed gigabit | Lab switching + VLANs | Tampa apartment |
| **MacBook Air M2** | Apple M2 · macOS 13.5 | Secondary management workstation | Tampa |

---

## Network Architecture

```
                            INTERNET
                                |
                  Apartment Router (172.20.x.x)
                  WARNING: NAT only, no port forwarding
                                |
                   +------------+------------+
                   |                         |
          OptiPlex (Ethernet)          ProBook (WiFi)
          172.20.16.175                172.20.x.x
                   |
         +---------------------+
         |   Proxmox VE 9.1.1  |
         +---------------------+
                   |
      +------------+-------------+
      |            |             |
  OPNsense       Kali         Splunk
  VM 200         VM 100       VM 101
  192.168.1.1    .100         .103
  (firewall)   (attack)      (SIEM)
      |
  TP-Link Switch
      |
  Raspberry Pi 5
  Pi-hole + Zeek


  IOWA -----------------------------------------------
  HP ProLiant DL360 G7
  Tailscale: 100.119.210.126
  +-- Wazuh 4.14 (manager + indexer + dashboard)
  +-- Windows Server 2022 AD lab (planned)
  +-- BloodHound lab (planned)

  TAILSCALE MESH (punches through apartment NAT)
  ---------------------------------------------------
  fedora (ProBook)    100.74.18.2
  macbook             100.104.62.66
  kali                100.77.251.92
  proxmox             100.90.195.73
  splunk              100.81.37.2
  raspberrypi         100.119.34.79
  proliant            100.119.210.126
```

**Key design decisions:**
- Apartment NAT blocks all inbound traffic — Tailscale solves remote access via outbound-only connections, no port forwarding required
- OPNsense runs as a Proxmox VM because Pi 5 cannot run it (ARM64 support was dropped)
- DNS chain: Lab VMs → OPNsense Unbound → Pi-hole → upstream resolvers
- ProLiant in Iowa handles workloads the OptiPlex HDD cannot sustain (Wazuh/OpenSearch require sustained I/O)

---

## Infrastructure Stack

### OptiPlex — Local Hypervisor

**Hardware:** Dell OptiPlex 7010 · i5-3570 @ 3.4GHz · 15.5GB RAM · spinning HDD

**Proxmox VE 9.1.1** — Bare metal Type 1 hypervisor. Web UI at `https://100.90.195.73:8006`.

**Setup process:**
- Flashed Proxmox ISO to USB via Balena Etcher on MacBook
- Booted OptiPlex from USB (F12 boot menu), installed to local disk
- Configured static IP, enabled SSH, installed Tailscale
- Created virtual network bridges: `vmbr0` (WAN/apartment) and `vmbr1` (lab LAN)

---

#### OPNsense `VM 200 · 192.168.1.1`

Virtual firewall and router. Handles all routing, NAT, DHCP, and DNS for the `192.168.1.x` lab subnet. Segments the lab from the apartment network completely.

**Configuration:**
- WAN interface: bridged to `vmbr0` (apartment network, gets DHCP from apartment router)
- LAN interface: bridged to `vmbr1` (lab subnet `192.168.1.0/24`)
- DNS: Unbound configured to forward all queries to Pi-hole at `172.20.17.132`
- DHCP: serving `192.168.1.100–200` range
- WireGuard instance configured for future road-warrior VPN use

**Why a VM instead of the Pi:** OPNsense and pfSense both dropped ARM64 support. The Pi 5 physically cannot run either. Virtual firewall on Proxmox is the correct solution for an apartment lab without a dedicated router.

---

#### Kali Linux `VM 100 · 192.168.1.100`

Primary attack platform. Full offensive toolkit. Tailscale installed for direct remote SSH access (`ssh kali@100.77.251.92`).

**Splunk Universal Forwarder** installed and configured to ship logs to `192.168.1.103:9997`. Currently forwarding 40,000+ events.

---

#### Splunk Enterprise 10.2.1 `VM 101 · 192.168.1.103`

SIEM. Web UI at `http://100.81.37.2:8000`.

**Ingesting logs from:**
- Kali Linux VM via Universal Forwarder
- ProBook (Fedora 43) via Universal Forwarder
- Total: 40,000+ events

**Setup:**
- Ubuntu Server VM on Proxmox
- Splunk Enterprise installed via `.deb`
- Universal Forwarder deployed on Kali and ProBook, pointing to `192.168.1.103:9997`
- Created dedicated index for lab data

**License:** Free perpetual after 60-day trial. 500MB/day ingest cap — sufficient for lab volumes.

---

### ProLiant — Remote Heavy-Lift Node

**Hardware:** HP ProLiant DL360 G7 · 2x Intel Xeon X5650 (12 cores/24 threads total) · 32GB DDR3 ECC RAM · 4x SAS drives · iDRAC remote management

**Location:** Iowa, co-located. Accessed exclusively via Tailscale (`100.119.210.126`). No physical access needed — iDRAC handles out-of-band management.

This server exists because the OptiPlex's spinning HDD causes I/O timeouts that kill OpenSearch and Elasticsearch initialization. Wazuh failed to install on the OptiPlex 8+ times across multiple methods. The ProLiant's SAS drives and 32GB ECC RAM handle it without issue.

**Proxmox VE** installed as hypervisor — same stack as local node.

---

#### Wazuh 4.14 *(deploying)*

Full HIDS/EDR stack: Wazuh Manager + OpenSearch Indexer + Dashboard.

**Why it failed on the OptiPlex:** Wazuh's quick-install script deploys OpenSearch, a Java-based Elasticsearch fork. On a spinning HDD, OpenSearch JVM initialization hits I/O timeouts during index mapping and cluster formation. After 8 documented failures (OVA import, quick install script, manual step-by-step, different Ubuntu versions), the root cause was hardware — not configuration.

**Why it works on the ProLiant:** SAS drives with adequate sustained IOPS. 32GB RAM means no swapping during Java heap allocation. Problem solved by moving to appropriate hardware.

**Planned agent deployment:**
- Kali Linux VM
- Splunk VM
- ProBook (Fedora 43)
- Windows Server VMs (when built)

**Dashboard:** `http://100.119.210.126:443` via Tailscale

---

#### Windows Server 2022 Active Directory Lab *(planned)*

Domain controller + domain-joined Windows 10/11 victim VMs.

**Attack scenarios to run:**
- BloodHound — enumerate AD, find attack paths to Domain Admin
- Kerberoasting — request service tickets, crack offline
- Pass-the-Hash — lateral movement with NTLM hashes
- DCSync — dump domain credentials via replication rights
- ASREPRoasting — target accounts without Kerberos pre-auth required

**Detection:** All Windows event logs forwarded to Wazuh agents → Splunk for correlation. Goal is to run the attack, watch it appear in the SIEM, and write detection rules.

---

### Raspberry Pi 5 — Perimeter Node

**Hardware:** Raspberry Pi 5 · BCM2712 quad-core Cortex-A76 · 8GB RAM · Vilros case with active cooler · official 27W USB-C PSU

**Location:** Tampa apartment, connected to TP-Link switch

---

#### Pi-hole

Network-wide DNS sinkhole. Every DNS query from every device on the lab network flows through Pi-hole before hitting upstream resolvers.

**DNS chain:** Lab VMs → OPNsense Unbound → Pi-hole (`172.20.17.132`) → `1.1.1.1` / `8.8.8.8`

**Why it matters for security:** Malware C2 beaconing shows up as anomalous DNS queries here before any other detection layer catches it. Real-time feed via `pihole -t` shows every DNS request on the network as it happens. Blocklists catch known malicious domains before connections are even attempted.

**Access:** `http://100.119.34.79/admin`

---

#### Zeek 8.1.1

Passive network traffic analysis engine on `eth0`. Captures and parses all network traffic into structured logs without transmitting anything.

**Log types:**
- `conn.log` — every TCP/UDP connection: source, dest, duration, bytes, state
- `dns.log` — every DNS query and response
- `http.log` — HTTP requests, methods, user agents, URIs, status codes
- `ssl.log` — TLS handshakes, certificate details, cipher suites
- `files.log` — files transferred over the network, hashes
- `weird.log` — protocol violations and anomalies

**Notable catches during setup:**
- TP-Link switch spamming DHCP DISCOVER from `192.168.0.1` — subnet mismatch, harmless but visible
- WireGuard traffic fingerprinted in `weird.log` via UDP checksum anomaly on own public IP

**Log location:** `/opt/zeek/logs/current/`

---

### ProBook 650 G8 — Attack Terminal

**Hardware:** HP ProBook 650 G8 · 11th Gen Intel i7-1165G7 (8 threads @ 2.8GHz boost) · 16GB DDR4 · 475GB NVMe SSD · Intel Iris Xe integrated graphics · 1920x1080 display

**OS:** Fedora 43 Workstation · Full-disk LUKS2 encryption (passphrase required on boot)

**Shell environment:**
- zsh + Oh My Zsh framework
- Powerlevel10k prompt (instant prompt enabled)
- zsh-autosuggestions + zsh-syntax-highlighting
- fzf fuzzy finder integrated into history and file search
- Custom `.p10k.zsh` configuration

**Terminal:** Ptyxis · tmux with custom prefix, split keybindings, and status bar

**Editor:** Neovim with full IDE stack:
- LSP (language server protocol) for code intelligence
- Treesitter for syntax highlighting
- Telescope for fuzzy file/grep search
- Catppuccin color theme
- Custom `init.lua` configuration

**System hardening:**
- Full-disk LUKS2 encryption
- `auditd` — kernel-level system call audit logging
- `fail2ban` — automatic SSH brute-force lockout
- `rkhunter` — rootkit scanning (498 checks, 0 warnings)
- `ClamAV` — on-demand malware scanning

**Infrastructure tooling:**
- Tailscale — zero-config mesh VPN to all lab nodes
- Splunk Universal Forwarder 10.2.2 — shipping local logs to SIEM
- Ansible — playbooks for lab node management and automation
- Remmina — RDP/VNC/SSH graphical remote desktop
- virt-manager — local VM management via libvirt/QEMU

---

#### Attack & Security Tooling

| Tool | Command / Access | Purpose |
|---|---|---|
| Metasploit 6.4 | `msfconsole` | Exploitation framework |
| Burp Suite Community | Desktop icon | Web app proxy and interceptor |
| Bettercap | `sudo bettercap` | Network attacks, ARP spoofing, WiFi |
| nmap | `nmap` | Network discovery and port scanning |
| Wireshark | Desktop icon | GUI packet capture and analysis |
| gobuster | `gobuster` | Directory and DNS brute-forcing |
| ffuf | `ffuf` | Fast web content fuzzing |
| hydra | `hydra` | Online credential brute-forcing |
| nikto | `nikto` | Web server vulnerability scanning |
| sqlmap | `sqlmap` | SQL injection detection and exploitation |
| Ghidra 12.0.4 | Desktop icon / `ghidra` | NSA reverse engineering framework |
| Radare2 | `r2` | Binary analysis, disassembly, debugging |
| Binwalk | `binwalk` | Firmware analysis and extraction |
| ImHex | `imhex` | Hex editor with pattern language |
| Steghide | `steghide` | Steganography — hide/extract data in images |
| ExifTool | `exiftool` | File metadata extraction and stripping |
| Proxychains | `proxychains <cmd>` | Force traffic through proxy chains |
| Aircrack-ng | `aircrack-ng` | WiFi packet capture and WEP/WPA cracking |
| Kismet | `sudo kismet` → `localhost:2501` | Passive wireless network detection |
| hcxdumptool | `sudo hcxdumptool` | WiFi PMKID/handshake capture |
| hcxtools | `hcxpcapngtool` | Convert WiFi captures for hashcat |
| Hashcat | `hashcat` | GPU-accelerated password cracking |
| John the Ripper | `john` | CPU password cracking |
| theHarvester | `theHarvester` | Email, subdomain, IP OSINT |
| Sherlock | `sherlock` | Username search across 300+ platforms |
| Maltego | Desktop icon | Visual link analysis (broken — Java compat issue) |
| SecLists | `/usr/share/seclists/` | Comprehensive security wordlist collection |

#### Privacy & Anonymity

| Tool | Access | Purpose |
|---|---|---|
| ProtonVPN | Desktop icon | Swiss VPN, no-logs, open source |
| Tor Browser | Desktop icon | Anonymous browsing via Tor network |
| KeePassXC | Desktop icon | Offline encrypted password manager |
| BleachBit | Desktop icon | Secure deletion and privacy cleaning |
| Signal | Desktop icon | E2E encrypted messaging |

#### Local AI

| Tool | Access | Purpose |
|---|---|---|
| Ollama | `ollama run llama3.2` | Local LLM inference — no internet required |
| llama3.2 (3.2B) | via Ollama | Installed local model |
| Open WebUI | `http://localhost:3000` | Browser-based ChatGPT-style UI for Ollama |

Open WebUI runs as a Docker container (`--restart always`) and survives reboots. Ollama connects via `http://172.17.0.1:11434`. Everything runs offline — zero data leaves the machine.

#### Hardware & Engineering

| Tool | Access | Purpose |
|---|---|---|
| Arduino IDE | Desktop icon | Microcontroller programming |
| KiCad | Desktop icon | Professional PCB design suite |
| Fritzing | Desktop icon | Breadboard circuit prototyping |
| Minicom | `sudo minicom -D /dev/ttyUSB0 -b 115200` | Serial terminal for embedded devices |
| Picocom | `sudo picocom /dev/ttyUSB0 -b 115200` | Lightweight serial terminal |

---

## Access Reference

| System | Address | Notes |
|---|---|---|
| Proxmox (local) | `https://100.90.195.73:8006` | OptiPlex hypervisor |
| Proxmox (Iowa) | `https://100.119.210.126:8006` | ProLiant hypervisor |
| Splunk Web | `http://100.81.37.2:8000` | SIEM dashboard |
| OPNsense | `https://192.168.1.1` | Firewall (lab network only) |
| Pi-hole | `http://100.119.34.79/admin` | DNS dashboard |
| Wazuh Dashboard | `http://100.119.210.126:443` | EDR/HIDS (deploying) |
| Open WebUI | `http://localhost:3000` | Local AI chat interface |
| Ollama API | `http://localhost:11434` | LLM inference API |

**SSH (all via Tailscale):**
```bash
ssh root@100.90.195.73      # proxmox (local)
ssh root@100.119.210.126    # proxmox (iowa / proliant)
ssh elijah@100.77.251.92    # kali
ssh elijah@100.81.37.2      # splunk
ssh elijah@100.119.34.79    # raspberry pi
```

---

## Tool Reference

**Network recon:**
```bash
nmap -sV -sC -A 192.168.1.0/24           # full subnet scan with service detection
nmap -p- --min-rate 5000 192.168.1.100   # all 65535 ports fast
```

**Web app recon:**
```bash
gobuster dir -u http://target -w /usr/share/seclists/Discovery/Web-Content/common.txt
ffuf -u http://target/FUZZ -w /usr/share/seclists/Discovery/Web-Content/raft-medium-files.txt
nikto -h http://target
sqlmap -u "http://target/page?id=1" --dbs
```

**WiFi auditing:**
```bash
airmon-ng start wlan0                     # monitor mode
airodump-ng wlan0mon                      # discover networks
sudo hcxdumptool -i wlan0 -o cap.pcapng --active_beacon
hcxpcapngtool cap.pcapng -o hashes.hc22000
hashcat -m 22000 hashes.hc22000 /usr/share/seclists/Passwords/WiFi-WPA/probable-v2-wpa-top4800.txt
```

**Password cracking:**
```bash
hashcat -m 0    hashes.txt wordlist.txt   # MD5
hashcat -m 1000 hashes.txt wordlist.txt   # NTLM (Windows)
hashcat -m 1800 hashes.txt wordlist.txt   # SHA-512 Unix
hashcat -m 22000 hashes.txt wordlist.txt  # WPA2
john --wordlist=/usr/share/seclists/Passwords/Leaked-Databases/rockyou.txt hashes.txt
```

**OSINT:**
```bash
theHarvester -d target.com -b all         # emails, subdomains, IPs from public sources
sherlock username                          # find username on 300+ platforms
exiftool image.jpg                         # extract GPS, device info from photo metadata
exiftool -all= image.jpg                   # strip all metadata before sharing
```

**Anonymity:**
```bash
proxychains nmap -sT target               # route nmap through proxy chain
# Edit /etc/proxychains.conf: add "socks5 127.0.0.1 9050" for Tor routing
```

**Reverse engineering:**
```bash
r2 binary                     # open in radare2
# r2 commands: aaa (analyze), pdf@main (disassemble main), VV (visual graph)
binwalk firmware.bin           # identify embedded files in firmware
binwalk -e firmware.bin        # extract embedded files
ghidra                         # launch Ghidra GUI RE framework
```

---

## Lessons Learned

**Wazuh on a spinning HDD is a non-starter.** OpenSearch requires sustained I/O that HDDs cannot provide. After 8 failed attempts on the OptiPlex (OVA import, quick-install script, manual install, multiple Ubuntu versions), the root cause was always hardware. Moving to the ProLiant's SAS drives solved it immediately. For any Java-based workload: SSD or don't bother.

**OPNsense and pfSense dropped ARM64.** The Pi 5 cannot run either. Run the firewall as a Proxmox VM. This is actually fine — the VM approach gives you snapshots, easy config backups, and the ability to roll back bad firewall rules.

**Apartment NAT kills WireGuard inbound.** The apartment router blocks all inbound UDP. WireGuard needs inbound connections. Tailscale uses outbound-only DERP relay connections and punches through NAT without any router access. Use it from day one — zero configuration, works everywhere, free for personal use.

**Memory ballooning starves Java workloads.** Proxmox's balloon driver dynamically restricts VM RAM to reclaim it for the host. Disable ballooning for Splunk and Wazuh VMs or watch them OOM silently under search load.

**University network blocks external DNS and specific domains.** Campus network (`spartans.ut`) blocks port 53 outbound and sinkholes certain domains (ProtonVPN, etc.). Workaround: DNS-over-HTTPS via `curl -s "https://1.1.1.1/dns-query?name=domain.com&type=A" -H "accept: application/dns-json"`, then hardcode resolved IPs in `/etc/hosts`.

**Ollama needs `0.0.0.0` binding for Docker containers to reach it.** By default Ollama only listens on `127.0.0.1`. Docker containers live on a different network interface and cannot reach localhost. Fix: `Environment="OLLAMA_HOST=0.0.0.0:11434"` in systemd override, then use the docker0 bridge IP (`172.17.0.1`) in Open WebUI settings.

**Ghidra requires the JDK, not just the JRE.** `java-21-openjdk` installs the runtime only — no `javac`. Ghidra needs the full development kit. Install `java-21-openjdk-devel` and manually specify the JDK path on first launch.

**Maltego is broken on Fedora 43.** Requires Java 11 or 17 which were removed from Fedora 43 repos. Only Java 21, 25, and 26 are available. Java 21+ removed Security Manager support that Maltego depends on. Workaround: Docker with an older Java base image.

**Document every failure.** Eight documented Wazuh install failures became the clearest explanation of why hardware matters. Every failure is a lesson that sticks harder than anything that works on the first try.

---

## Roadmap

- [x] Proxmox VE hypervisor on OptiPlex
- [x] OPNsense virtual firewall and router
- [x] Kali Linux attack VM
- [x] Pi-hole DNS sinkhole
- [x] Zeek 8.1.1 passive network monitoring
- [x] Tailscale mesh VPN across all nodes
- [x] Splunk Enterprise 10.2.1 SIEM
- [x] Universal Forwarder — Kali → Splunk
- [x] Universal Forwarder — ProBook → Splunk
- [x] HP ProBook 650 G8 attack terminal (Fedora 43, LUKS encrypted)
- [x] Full offensive toolkit (Metasploit, Burp, aircrack-ng, Ghidra, etc.)
- [x] Ansible automation for lab node management
- [x] ProtonVPN + Tor anonymity layer
- [x] Local AI stack (Ollama + llama3.2 + Open WebUI)
- [x] Hardware engineering tools (Arduino IDE, KiCad, Fritzing)
- [x] Dotfiles repository
- [ ] **Wazuh 4.14 full stack on ProLiant** ← in progress
- [ ] Wazuh agents deployed to all nodes
- [ ] Windows Server 2022 Active Directory lab
- [ ] BloodHound AD enumeration
- [ ] Attack scenarios: Kerberoasting, Pass-the-Hash, DCSync, ASREPRoasting
- [ ] Wazuh → Splunk alert forwarding and correlation rules
- [ ] Detection engineering for AD attack patterns
- [ ] CTF writeups
- [ ] Rubber Ducky / BadUSB payload lab
- [ ] AWS/Azure cloud integration
- [ ] Network traffic visualization (Grafana + Zeek logs)
- [ ] Metasploitable target VM for practice

---

<div align="center">

**B.S. Cybersecurity** *(in progress)* · **CompTIA Security+** · **Microsoft AZ-900**

*Certs teach you concepts. Labs teach you how things actually break.*

</div>
