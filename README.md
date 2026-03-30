```
██╗      █████╗ ██████╗     ███████╗███████╗ ██████╗
██║     ██╔══██╗██╔══██╗    ██╔════╝██╔════╝██╔════╝
██║     ███████║██████╔╝    ███████╗█████╗  ██║
██║     ██╔══██║██╔══██╗    ╚════██║██╔══╝  ██║
███████╗██║  ██║██████╔╝    ███████║███████╗╚██████╗
╚══════╝╚═╝  ╚═╝╚═════╝     ╚══════╝╚══════╝ ╚═════╝
```

<div align="center">

![Status](https://img.shields.io/badge/status-active-00ff88?style=for-the-badge&labelColor=0d1117)
![Splunk](https://img.shields.io/badge/Splunk-10.2.1-ff6b35?style=for-the-badge&labelColor=0d1117)
![Proxmox](https://img.shields.io/badge/Proxmox-9.1-e57000?style=for-the-badge&labelColor=0d1117)
![Tailscale](https://img.shields.io/badge/Tailscale-connected-4a9eff?style=for-the-badge&labelColor=0d1117)

**A hands-on enterprise-grade security lab built from commodity hardware.**
Attack. Detect. Defend. Repeat.

</div>

---

## Hardware

| Device | Specs | Role |
|--------|-------|------|
| Dell OptiPlex 7010 | i5-3570 @ 3.4GHz · 15.5GB RAM · HDD | Primary hypervisor |
| HP ProLiant DL360 G7 | 2x X5650 Xeon · 32GB RAM · 4x SAS | Remote lab node (Iowa) |
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

Raspberry Pi 5 ─────── 172.20.17.132 / Tailscale: 100.119.34.79
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

**Wazuh 4.14** *(in progress)* — Full stack: manager, indexer, dashboard. Moved here from the OptiPlex after HDD timeouts killed OpenSearch initialization repeatedly. 32GB RAM and SAS drives handle it properly.

**Active Directory Lab** *(planned)* — Windows Server 2022 domain controller + domain-joined Windows 10/11 victim VMs. BloodHound enumeration, Kerberoasting, Pass-the-Hash, DCSync attacks from Kali — detection in Wazuh and Splunk.

---

### Raspberry Pi 5 — Perimeter Node

**Pi-hole** — Network-level DNS sinkhole. All lab DNS routes through it. Logs every query — malware beaconing shows up here before anything else.

**Zeek 8.1.1** — Passive network monitoring on `eth0`. Generates structured logs for connections, DNS, HTTP, SSL, and file transfers. Sits outside the OPNsense perimeter for a different vantage point.

**Tailscale** — Enrolled on all lab nodes. Bypasses apartment NAT via outbound-only connections. No port forwarding required.

---

## What's Running

```
elijah@splunk:~$ splunk search "index=* host=kali" | stats count
41,949 events indexed from Kali Linux
Sources: /var/log/* (dpkg, auth, syslog, lightdm, apt)
Pipeline: Kali → Universal Forwarder → Splunk:9997 → indexed
```

---

## Lessons Learned (the hard way)

**Memory ballooning will starve your VMs.** Proxmox's balloon driver dynamically restricts RAM. OpenSearch, Splunk, and any Java-based workload needs full allocation at startup — disable ballooning.

**HDDs and OpenSearch don't mix.** First-time index initialization on a spinning disk is too slow. The Wazuh installer's hardcoded timeout fires before OpenSearch becomes healthy. SSD or bust.

**OPNsense and pfSense dropped ARM64.** The Pi cannot run either. Hypervisor VM is the correct approach for the firewall role.

**Apartment NAT kills WireGuard.** Inbound UDP is blocked at the upstream router. Tailscale uses outbound-only connections and punches through NAT without port forwarding. Use it from the start.

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
|--------|---------|
| Proxmox (local) | `https://100.90.195.73:8006` |
| Proxmox (remote) | `https://100.119.210.126:8006` |
| Splunk Web | `http://100.81.37.2:8000` |
| OPNsense | `https://192.168.1.1` |
| Pi-hole | `http://172.20.17.132/admin` |
| Kali SSH | `ssh kali@100.77.251.92` |
| Splunk SSH | `ssh elijah@100.81.37.2` |
| Pi SSH | `ssh elijah@100.119.34.79` |

---

<div align="center">

**B.S. Cybersecurity (in progress) · CompTIA Security+ · Microsoft AZ-900**

*Certs teach you concepts. Labs teach you how things actually break.*

</div>
