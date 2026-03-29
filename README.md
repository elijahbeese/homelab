# 🏠 Elijah's Cybersecurity Homelab

> A hands-on enterprise-grade security lab built from commodity hardware — designed for SIEM, EDR, Active Directory attack/defense, network monitoring, and offensive security practice.

---

## 📋 Table of Contents

- [Hardware Inventory](#hardware-inventory)
- [Network Architecture](#network-architecture)
- [Infrastructure Overview](#infrastructure-overview)
- [Component Deep Dives](#component-deep-dives)
  - [Proxmox VE](#proxmox-ve)
  - [OPNsense Firewall](#opnsense-firewall)
  - [Kali Linux](#kali-linux)
  - [Raspberry Pi 5](#raspberry-pi-5)
  - [Pi-hole](#pi-hole)
  - [Zeek](#zeek)
  - [Tailscale](#tailscale)
- [Wazuh SIEM — Installation Journey & Lessons Learned](#wazuh-siem--installation-journey--lessons-learned)
- [Key Learnings](#key-learnings)
- [Credentials & IP Reference](#credentials--ip-reference)
- [Offensive Tools](#offensive-tools)
- [Roadmap — What Comes Next](#roadmap--what-comes-next)

---

## Hardware Inventory

| Device | Specs | Role |
|--------|-------|------|
| Dell OptiPlex 7010 | Intel i5-3570 @ 3.40GHz, 15.51GB RAM, 93.93GB HDD | Proxmox hypervisor host |
| Raspberry Pi 5 | 8GB RAM, Vilros kit | DNS, network monitoring, remote access |
| TP-Link TL-SG108E | 8-port managed switch | Lab network switching |
| UGREEN 2.5Gb USB Ethernet | USB-C adapter | MacBook → lab connectivity |
| MacBook Air M2 | macOS 13.5 | Management workstation |

> **Note on the HDD:** The OptiPlex runs a spinning disk, not an SSD. This caused significant pain during Wazuh installation (OpenSearch's first-time initialization times out on HDDs). Future upgrade to an SSD is strongly recommended.

---

## Network Architecture

```
Internet
    │
    ▼
Apartment Router (172.20.x.x) ← CANNOT ACCESS — no port forwarding
    │
    ├── MacBook Air M2 (WiFi) ─────────────────────── 172.20.x.x
    │
    └── Dell OptiPlex (Ethernet) ─────────────────── 172.20.16.175
            │
            └── Proxmox VE
                    │
                    ├── vmbr0 (bridged to physical NIC)
                    │       └── OPNsense WAN face
                    │
                    └── vmbr1 (internal virtual switch)
                            │
                            ├── OPNsense LAN ─── 192.168.1.1/24
                            ├── Kali Linux ────── 192.168.1.100
                            └── Wazuh VM ─────── 192.168.1.102

Raspberry Pi 5 ──────────────────────────────────── 172.20.17.132
    └── Pi-hole DNS
    └── Zeek (monitoring eth0)
    └── x11vnc / RealVNC

Tailscale Overlay Network (bypasses apartment NAT):
    ├── Proxmox host ───── 100.90.195.73
    ├── Kali Linux ─────── 100.72.251.62
    └── Raspberry Pi 5 ─── 100.119.34.79
```

### Why Tailscale Instead of WireGuard

The apartment network uses per-resident isolation and blocks all inbound connections. Port forwarding is impossible without access to the upstream router. WireGuard on OPNsense was attempted but abandoned — it requires inbound UDP connectivity that the apartment router silently drops.

**Tailscale uses outbound connections only**, punching through NAT via DERP relay servers. No port forwarding required. It creates a flat overlay network across all lab devices regardless of where they physically sit.

---

## Infrastructure Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Proxmox VE 9.1.1                         │
│                     172.20.16.175 (host)                        │
│                                                                  │
│  ┌──────────────────┐   ┌──────────────────┐   ┌─────────────┐ │
│  │  VM 200          │   │  VM 100          │   │  VM 101     │ │
│  │  OPNsense        │   │  Kali Linux      │   │  Wazuh      │ │
│  │  Firewall/Router │   │  Attack Platform │   │  SIEM       │ │
│  │  192.168.1.1     │   │  192.168.1.100   │   │  192.168.1.102│
│  └──────────────────┘   └──────────────────┘   └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Raspberry Pi 5 (8GB)                       │
│                       172.20.17.132                             │
│                                                                  │
│   Pi-hole (DNS)   │   Zeek 8.1.1   │   x11vnc / RealVNC        │
│   Port 53/80      │   eth0 monitor │   Remote desktop           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Deep Dives

### Proxmox VE

**What it is:** Proxmox Virtual Environment is an open-source Type-1 hypervisor built on Debian + KVM. It lets you run multiple virtual machines and containers on a single physical host with a web-based management interface.

**Why it's here:** The OptiPlex is the only dedicated lab machine. Without virtualization, you'd be limited to one OS at a time. Proxmox lets a single box run a firewall, an attacker machine, a SIEM, an Active Directory server, and victim machines simultaneously.

**Key configuration:**
- Web UI: `https://172.20.16.175:8006` (or via Tailscale: `https://100.90.195.73:8006`)
- Version: 9.1.1
- CPU: Intel i5-3570 @ 3.40GHz (4 cores, 1 socket)
- Total RAM: 15.51GB
- Storage: 93.93GB (local-lvm)
- Network bridges: `vmbr0` (WAN/physical), `vmbr1` (internal lab network)
- GUI: XFCE + LightDM installed on host; login as user `elijah`

**Lessons learned:**
- OPNsense and pfSense dropped ARM64 support — the Pi cannot run them. Proxmox VM is the correct approach.
- Memory ballooning causes VMs to starve during heavy workloads. Disable it for VMs that need full RAM allocation.
- The `elijah` user was created for GUI login after root GUI access issues with LightDM.

---

### OPNsense Firewall

**What it is:** OPNsense is an open-source firewall/router OS based on FreeBSD. It handles routing, NAT, DHCP, DNS, and traffic rules between the lab's internal network and the outside world.

**Why it's here:** Every enterprise network has a firewall. Running OPNsense teaches real-world firewall administration — interface configuration, NAT rules, DHCP scopes, DNS resolution, VPN setup, and IDS/IPS integration (Suricata can be added later).

**Configuration:**
- VM ID: 200
- WAN interface: `vtnet0` on `vmbr0` — faces the apartment network
- LAN interface: `vtnet1` on `vmbr1` — internal lab network
- LAN IP: `192.168.1.1/24`
- DHCP range: `192.168.1.100 – 192.168.1.200`
- DNS: Unbound configured to forward queries to Pi-hole at `172.20.17.132`

**What it protects:** All lab VMs on the `192.168.1.x` subnet sit behind OPNsense. Traffic between VMs is controlled by firewall rules. Kali can attack victims without affecting the real network.

---

### Kali Linux

**What it is:** Kali Linux is a Debian-based penetration testing distribution maintained by Offensive Security. It comes pre-loaded with hundreds of offensive security tools.

**Why it's here:** The attack platform. Use it to run exploits, run BloodHound enumeration, execute Rubber Ducky payloads against victim VMs, perform network scans, and generally act as the threat actor in lab scenarios.

**Configuration:**
- VM ID: 100
- IP: `192.168.1.100` (DHCP from OPNsense)
- Tailscale IP: `100.72.251.62`
- Sits on `vmbr1` — same network as all other lab VMs

**Key tools available:** Metasploit, nmap, Burp Suite, BloodHound, netcat, Wireshark, John the Ripper, Hydra, aircrack-ng, and many more.

---

### Raspberry Pi 5

**What it is:** A small single-board computer running Raspberry Pi OS (Debian-based). In this lab it acts as a dedicated services node — DNS filtering, network monitoring, and remote desktop relay.

**Why it's here:** Always-on, low-power device that runs services that need to be up 24/7 without consuming OptiPlex resources. It also sits on the *apartment* network (`172.20.x.x`) — outside the lab's OPNsense perimeter — giving it visibility into traffic that OPNsense never sees.

**Configuration:**
- IP: `172.20.17.132` (apartment network, DHCP)
- Tailscale IP: `100.119.34.79`
- Running: Pi-hole, Zeek 8.1.1, x11vnc, RealVNC
- Remote desktop: accessible via RealVNC or `ssh -L` tunnel

> **Note:** OPNsense and pfSense both dropped ARM64 support, making the Pi unsuitable as a firewall host. Proxmox VM on the OptiPlex is the correct approach for the firewall role.

---

### Pi-hole

**What it is:** Pi-hole is a network-level DNS sinkhole. DNS queries from all lab devices route through it. Known ad/tracking/malware domains are blocked before a connection is ever made.

**Why it's here:** DNS visibility is critical for security monitoring. Pi-hole logs every DNS query in the lab, giving you a record of what domains each machine tried to resolve. It also demonstrates DNS-based threat intelligence — the same principle used by enterprise tools like Cisco Umbrella.

**Configuration:**
- Runs on the Pi at `172.20.17.132`
- Web dashboard: `http://172.20.17.132/admin`
- OPNsense Unbound is configured to forward all DNS queries to Pi-hole
- DNS traffic confirmed flowing through Pi-hole via query log verification

**Security value:** Any malware in the lab that beacons to a C2 domain will show up in Pi-hole logs. Any VM doing unexpected DNS lookups stands out immediately.

---

### Zeek

**What it is:** Zeek (formerly Bro) is a network analysis framework that passively monitors traffic and generates structured logs — connections, DNS queries, HTTP requests, SSL certificates, file transfers, and more. It is not an IDS — it doesn't alert, it *records*.

**Why it's here:** Real network visibility. Zeek gives you the same kind of network telemetry that enterprise SOC teams use to hunt threats and investigate incidents. Every connection through the Pi's network interface gets logged with full metadata.

**Configuration:**
- Version: 8.1.1
- Installed from OpenSUSE security repository (not default Raspberry Pi OS repos, which had outdated versions)
- Monitoring interface: `eth0` on the Pi
- Log location: `/opt/zeek/logs/` (or similar depending on install path)

**What it captures:** Connection records (src/dst IP, port, protocol, duration, bytes), DNS queries and responses, HTTP metadata, SSL/TLS certificate details, and more.

**Future use:** Feed Zeek logs into Wazuh or Splunk for correlation with endpoint events.

---

### Tailscale

**What it is:** Tailscale is a zero-config VPN built on WireGuard. Each enrolled device gets a stable IP on a shared `100.x.x.x` network. It uses NAT traversal techniques to connect devices directly without requiring port forwarding.

**Why it's here:** The apartment network blocks all inbound connections. WireGuard on OPNsense was attempted and abandoned — it requires inbound UDP that the upstream router drops. Tailscale uses only *outbound* connections and punches through NAT automatically.

**Enrolled devices:**

| Device | Tailscale IP |
|--------|-------------|
| Proxmox host | `100.90.195.73` |
| Kali Linux VM | `100.72.251.62` |
| Raspberry Pi 5 | `100.119.34.79` |

**Result:** SSH into any lab device from anywhere in the world:
```bash
ssh root@100.90.195.73     # Proxmox host
ssh kali@100.72.251.62     # Kali VM
ssh elijah@100.119.34.79   # Raspberry Pi
```

---

## Wazuh SIEM — Installation Journey & Lessons Learned

This section documents the full Wazuh installation process, including every failure encountered and why it happened. This is intentional — understanding *why* things break is the actual learning.

### What is Wazuh?

Wazuh is an open-source SIEM/XDR platform. It consists of three components:

| Component | Role |
|-----------|------|
| **Wazuh Manager** | Core server. Receives agent data, runs detection rules, generates alerts |
| **Wazuh Indexer** | OpenSearch-based data store. Indexes and stores all events and alerts |
| **Wazuh Dashboard** | Web UI built on OpenSearch Dashboards. Visualizes alerts, agents, compliance |

Agents are installed on endpoints (Windows VMs, Linux servers, etc.) and ship logs + system events to the Manager.

### VM Specifications (Final Working Config)

- **VM ID:** 101
- **OS:** Ubuntu 22.04.5 LTS
- **CPU:** 4 cores (2 sockets × 2 cores)
- **RAM:** 8GB (ballooning DISABLED — critical)
- **Disk:** 50GB (local-lvm)
- **Network:** `vmbr1`, IP `192.168.1.102`
- **Wazuh version:** 4.14.4

### Installation Failures & Root Causes

#### Failure 1: ISO not detaching after install
**Symptom:** `[FAILED] Failed unmounting /cdrom` on boot  
**Cause:** Proxmox still had the Ubuntu ISO attached to the VM's CD/DVD drive after installation completed  
**Fix:** Hardware tab → CD/DVD Drive → Edit → "Do not use any media" → press Enter in console

#### Failure 2: Wrong download URL
**Symptom:** `Error:Code:AccessDenied` when running `curl -sO https://packages.wazuh.com/4.x/wazuh-install.sh`  
**Cause:** The `4.x` URL path no longer works. Wazuh moved to versioned paths.  
**Fix:** Use `https://packages.wazuh.com/4.14/wazuh-install.sh`

#### Failure 3: UFW blocking outbound curl
**Symptom:** Access Denied on curl even with correct URL  
**Cause:** UFW (Ubuntu's firewall) was enabled and blocking outbound HTTPS  
**Fix:** `sudo ufw disable` — acceptable for a lab environment

#### Failure 4: Memory ballooning starving the VM
**Symptom:** `free -h` showed only 240MB available despite 4GB allocated in Proxmox  
**Cause:** Proxmox's memory balloon driver dynamically restricts RAM to idle VMs. OpenSearch needs full allocation available immediately  
**Fix:** Hardware → Memory → Edit → uncheck "Ballooning Device"

#### Failure 5: Wazuh dashboard timeout on HDD
**Symptom:** Everything installs except the dashboard. Script times out waiting for OpenSearch to start.  
**Cause:** The OptiPlex runs a **spinning HDD** (`/sys/block/sda/queue/rotational` returns `1`). OpenSearch's first-time index initialization on a HDD is too slow — the installer's hardcoded timeout expires before OpenSearch becomes healthy.  
**Root cause confirmed:** `sudo bash wazuh-install.sh -a` consistently failed at dashboard stage across 3+ attempts even with 8GB RAM and 4 cores.

#### Failure 6: Zombie Wazuh processes blocking reinstall
**Symptom:** `ERROR: Port 515 is being used by another process`  
**Cause:** `wazuh-authd` survived the installer's cleanup and was still listening on port 515  
**Fix:** `sudo pkill -9 wazuh-authd` + `sudo systemctl stop wazuh-manager`

#### Failure 7: Corrupted dpkg state
**Symptom:** `dpkg: error processing package wazuh-manager (--remove): subprocess returned error exit status 127`  
**Cause:** Multiple failed partial installs left dpkg in an inconsistent state  
**Fix:** `sudo dpkg --configure -a && sudo apt --fix-broken install -y`

#### Failure 8: Missing keystore binary
**Symptom:** `wazuh-install.sh: line 1394: /var/ossec/bin/wazuh-keystore: No such file or directory`  
**Cause:** Cumulative corruption from 8+ failed install attempts. The package installed but critical binaries were missing.  
**Resolution:** VM nuked. Fresh Ubuntu install required.

### The Right Approach (Do This Next Time)

```bash
# 1. Ensure VM has: 8GB RAM (ballooning OFF), 50GB disk, 4 cores, Ubuntu 22.04 fresh install

# 2. Disable UFW
sudo ufw disable

# 3. Download the installer (note: versioned URL, not 4.x)
curl -o wazuh-install.sh https://packages.wazuh.com/4.14/wazuh-install.sh

# 4. Run the all-in-one installer
sudo bash wazuh-install.sh -a

# If on HDD and dashboard times out, use step-by-step:
curl -o config.yml https://packages.wazuh.com/4.14/config.yml
# Edit config.yml: replace all placeholder IPs with 192.168.1.102
sudo bash wazuh-install.sh -g            # Generate certs
sudo bash wazuh-install.sh -wi node-1   # Install indexer
sudo bash wazuh-install.sh -ws wazuh-1  # Install server
# Then manually install dashboard package via apt
```

### SSH Access Issues Encountered

SSH from Mac directly to `192.168.1.102` timed out because the Mac (on apartment WiFi) cannot route to `192.168.1.x` (behind OPNsense on the lab ethernet). Solutions:

```bash
# Option 1: Jump through Proxmox host
ssh -J root@100.90.195.73 elijah@192.168.1.102

# Option 2: From existing Proxmox SSH session
ssh elijah@192.168.1.102

# Option 3: Add Wazuh VM to Tailscale (cleanest long-term solution)
```

---

## Key Learnings

### Networking
- **Apartment NAT is a hard constraint.** Inbound connections are blocked. Port forwarding is impossible. Design around this with Tailscale from the start.
- **Per-resident network isolation** means WiFi (Mac) and ethernet (lab) are on separate subnets. Don't assume they can talk to each other.
- **OPNsense/pfSense dropped ARM64.** Never put a firewall on the Pi. Hypervisor VMs only.

### Virtualization
- **Memory ballooning is hostile to memory-hungry workloads.** Disable it for any VM running Java (OpenSearch, Elasticsearch, Splunk) or databases.
- **VMs remember their install cruft.** When multiple partial installs corrupt a VM, nuke it and start fresh. Fighting dpkg inconsistency is a time sink.
- **Always check `rotational` before installing OpenSearch-family software.** HDDs cannot meet the startup timeouts.

### Security Architecture
- **DNS is a gold mine for detection.** Pi-hole logs reveal beaconing, C2 communication, and unexpected outbound activity before any other indicator.
- **Network monitoring outside the perimeter** (Zeek on the apartment network) sees traffic that the internal firewall never processes — valuable different vantage point.
- **Layer your visibility:** endpoint (Wazuh agents) + network (Zeek) + DNS (Pi-hole) = three independent data sources to correlate.

### Tools & Operational
- **Proxmox noVNC clipboard is terrible.** Always SSH in for anything beyond trivial commands. Use jump hosts when direct SSH isn't available.
- **Screenshot your credentials.** Wazuh's installer prints admin credentials once at the end. If the terminal scrolls or the session dies, they're gone.
- **`curl -sO` saves to current directory.** Always `cd ~` first so you know where things land.

---

## Credentials & IP Reference

| System | Access | Notes |
|--------|--------|-------|
| Proxmox Web UI | `https://100.90.195.73:8006` | root / [set during install] |
| OPNsense Web UI | `https://192.168.1.1` | admin / [set during install] |
| Kali Linux | SSH `kali@100.72.251.62` | |
| Pi SSH | `ssh elijah@100.119.34.79` | |
| Pi-hole Dashboard | `http://172.20.17.132/admin` | |
| Wazuh Dashboard | `https://192.168.1.102:443` | admin / [printed at install end] |
| Wazuh VM SSH | `ssh -J root@100.90.195.73 elijah@192.168.1.102` | |

---

## Offensive Tools

### Rubber Ducky
A USB HID (Human Interface Device) attack tool. Plugs into a target machine and types keystrokes faster than any human. The OS sees it as a keyboard — not a USB drive — bypassing most USB security controls.

**Lab use cases:**
- Payload delivery to Windows victim VMs (once AD lab is built)
- Persistence mechanism testing
- Credential harvesting demos
- Detection engineering: run payloads against Wazuh-instrumented endpoints and tune rules to catch them
- DuckyScript payload development

### WiFi Pineapple
A dedicated wireless attack platform for rogue AP, evil twin, and deauth attacks.

**Lab use cases (requires isolated network):**
- Evil twin / captive portal credential capture
- Deauth testing against wireless clients
- Rogue AP detection (set it up, see if Zeek catches it)
- OSWP exam prep

> ⚠️ **Legal note:** Only use the Pineapple on networks you own and control, with no other users. A dedicated travel router or isolated hotspot is the correct lab setup. Do not operate on shared or apartment networks.

---

## Roadmap — What Comes Next

### Immediate (next session)
- [ ] Rebuild Wazuh VM with fresh Ubuntu 22.04
- [ ] Complete Wazuh all-in-one installation
- [ ] Add Wazuh VM to Tailscale for clean remote access
- [ ] Install Wazuh agent on Kali VM
- [ ] Verify alerts flowing to dashboard

### Short Term
- [ ] **Windows Server 2019/2022 VM** — Active Directory domain controller
- [ ] **Windows 10/11 VM** — Domain-joined workstation (victim machine)
- [ ] BloodHound enumeration of AD environment
- [ ] Run Kali attacks against AD, observe in Wazuh

### Medium Term
- [ ] **Splunk** — stand up alongside Wazuh for comparison; learn SPL queries
- [ ] Feed Zeek logs into Wazuh for network + endpoint correlation
- [ ] Rubber Ducky payload lab — execute against victim VM, tune detection
- [ ] Suricata IDS on OPNsense for inline threat detection

### Long Term
- [ ] **AWS/Azure integration** — cloud SIEM ingestion, hybrid lab scenarios
- [ ] SolarWinds familiarity (Orion platform basics)
- [ ] Physical firewall hardware (pfSense box or Fortinet)
- [ ] Dedicated server hardware upgrade (more RAM, SSD — critical for Splunk/OpenSearch)
- [ ] OSWP certification prep using WiFi Pineapple
- [ ] eJPT or PNPT certification

### Hardware Upgrades to Prioritize
1. **SSD for the OptiPlex** — HDDs are the #1 bottleneck for this lab. OpenSearch, Splunk, and any database workload will suffer on spinning rust. A 500GB SATA SSD is ~$40 and removes an entire category of problems.
2. **More RAM** — 16GB total limits concurrent VM count. 32GB opens up running AD controller + victim + SIEM + Kali simultaneously without contention.

---

## Lab Diagram

```
                    ┌─────────────────────────────────────────────────────┐
                    │              TAILSCALE OVERLAY                       │
                    │   Proxmox: 100.90.195.73                            │
                    │   Kali:    100.72.251.62                            │
                    │   Pi:      100.119.34.79                            │
                    └─────────────────────────────────────────────────────┘
                                        │ (encrypted tunnel)
                                        │
MacBook Air M2 ─────────────────────────┘
(Management)

                    APARTMENT NETWORK (172.20.x.x)
                    ────────────────────────────────
                    │                   │
           OptiPlex 7010         Raspberry Pi 5
           172.20.16.175         172.20.17.132
                │                    │
         Proxmox VE              Pi-hole (DNS :53)
                │                Zeek (eth0 monitor)
    ┌───────────┼───────────┐    RealVNC/x11vnc
    │           │           │
  VM 200      VM 100      VM 101
  OPNsense    Kali Linux   Wazuh SIEM
  (firewall)  (attacker)   (detection)
  192.168.1.1 .100         .102
    │
    └── DHCP: 192.168.1.100-200
    └── DNS forward → 172.20.17.132 (Pi-hole)
```

---

*Built by Elijah — B.S. Cybersecurity candidate, CompTIA Security+, Microsoft AZ-900*  
*Lab purpose: Hands-on skill development, portfolio evidence, and certification prep*
