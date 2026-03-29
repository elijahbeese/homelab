🏠 homelab

A cybersecurity-focused homelab built from scratch on a Dell OptiPlex 7010 and Raspberry Pi 5. Designed for hands-on practice with enterprise networking, offensive security, threat detection, and cloud integration.


📦 Hardware
DeviceRoleDell OptiPlex 7010Proxmox hypervisor — runs all VMsRaspberry Pi 5 (8GB)Pi-hole DNS + Zeek network monitorTP-Link TL-SG108EManaged switch for VLAN segmentationMacBook Air M2Management workstation

🧱 Architecture
Internet
   │
Apartment Router (172.20.x.x)
   │
OPNsense VM (Proxmox) ── WAN: 172.20.17.47
   │                  └── LAN: 192.168.1.1/24
Managed Switch
   ├── Proxmox Host (172.20.16.175)
   ├── Kali Linux VM (192.168.1.x)
   └── Raspberry Pi 5 (192.168.1.x)

🖥️ Virtual Machines
VMOSPurpose100Kali Linux 2025.4Offensive security / penetration testing200OPNsense 25.1Firewall, routing, VPN, IDSTBDSplunkSIEM / log aggregationTBDWindows ServerActive Directory labTBDMetasploitableVulnerable target for practice

🔧 What's Been Built
Phase 1 — Infrastructure

 Installed Proxmox VE 9.1 on bare metal (OptiPlex 7010)
 Deployed OPNsense 25.1 as virtual firewall/router
 Deployed Kali Linux 2025.4 VM for offensive ops
 Configured virtual networking between VMs

Phase 2 — Remote Access

 Configured WireGuard VPN on OPNsense (instance + peers + firewall rules)
 Installed Tailscale on Proxmox host and Kali VM
 Remote access to Proxmox web UI from anywhere via Tailscale (100.90.195.73:8006)
 Remote SSH into Kali from anywhere via Tailscale (100.72.251.62)

Phase 3 — Monitoring Stack (In Progress)

 Pi-hole on Raspberry Pi 5 — DNS filtering + query logging
 Zeek on Raspberry Pi 5 — network traffic analysis
 Wazuh on Proxmox — SIEM + host-based intrusion detection
 Feed Pi-hole + Zeek logs into Wazuh

Phase 4 — Lab Scenarios (Planned)

 Active Directory attack/defend lab (Windows Server + BloodHound + Mimikatz)
 Splunk deployment + detection engineering
 Metasploitable target network
 AWS/Azure cloud integration
 SolarWinds familiarity lab


🌐 Remote Access
ServiceAddressProxmox Web UIhttps://100.90.195.73:8006Kali SSHssh elijah@100.72.251.62OPNsense Web UIhttps://192.168.1.1 (LAN only)
Remote access is handled via Tailscale — no port forwarding required, works behind any NAT.

🔒 Security Stack
ToolPurposeOPNsenseFirewall, NAT, WireGuard VPNPi-holeDNS filtering, ad blocking, query loggingZeekPassive network traffic analysisWazuhSIEM, HIDS, log aggregationTailscaleZero-config remote access mesh VPN

🎯 Goals
This lab exists to build hands-on experience with:

Enterprise networking (VLANs, firewalls, routing)
Offensive security tooling (Kali, Metasploit, BloodHound)
Defensive security operations (SIEM, IDS, log analysis)
Cloud platforms (AWS, Azure)
Resume-worthy portfolio projects before entering the cybersecurity workforce


📚 Certs & Background

B.S. Cybersecurity (graduating May 2026)
CompTIA Security+
Microsoft AZ-900


🚧 Status
Active development. New VMs, services, and attack/defense scenarios added regularly.

Built on a Saturday night with too much coffee and a concerning amount of WireGuard suffering.
