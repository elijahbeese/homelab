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

## Table of Contents

- [Infrastructure](#infrastructure)
- [Hacker Laptop — Fedora 43](#hacker-laptop--fedora-43)
  - [Privacy & VPN](#privacy--vpn)
  - [Browsers & Anonymity](#browsers--anonymity)
  - [Offensive Security Tools](#offensive-security-tools)
  - [WiFi & Wireless Auditing](#wifi--wireless-auditing)
  - [Reverse Engineering & Forensics](#reverse-engineering--forensics)
  - [OSINT](#osint)
  - [Password Cracking](#password-cracking)
  - [Network Tools](#network-tools)
  - [AI & Local LLM](#ai--local-llm)
  - [Engineering & Hardware](#engineering--hardware)
  - [Privacy & System Tools](#privacy--system-tools)
  - [Wordlists & Payloads](#wordlists--payloads)
- [Installation Notes & Gotchas](#installation-notes--gotchas)

---

## Infrastructure

| Component | Role | Specs |
|---|---|---|
| Dell OptiPlex | Proxmox Hypervisor | i5, 16GB RAM, 512GB SSD |
| Raspberry Pi 5 | OPNsense Router/Firewall | 8GB RAM |
| TP-Link Switch | Network switching | 8-port unmanaged |
| HP Laptop (this machine) | Hacker Laptop | i7-1165G7, 16GB RAM, Iris Xe |

**VMs running on Proxmox:**
- Kali Linux — primary attack VM
- Metasploitable — intentionally vulnerable target
- Wazuh — SIEM/EDR
- Ubuntu Server — general purpose

---

## Hacker Laptop — Fedora 43

**Hardware:** HP laptop, 11th Gen Intel i7-1165G7 (8 cores @ 2.8GHz), 16GB RAM, Intel Iris Xe Graphics
**OS:** Fedora 43 Workstation
**Shell:** zsh + Oh My Zsh + Powerlevel10k

---

### Privacy & VPN

#### ProtonVPN
**What it is:** Privacy-focused VPN with a strict no-logs policy, based in Switzerland. Open source and independently audited.

**Access:** Desktop icon or terminal
```bash
proton-vpn-gnome-desktop
```

**Use cases:**
- Encrypt traffic on untrusted networks
- Bypass geo-restrictions
- Hide traffic from ISP/university network monitoring
- Route traffic through Secure Core servers for extra anonymity

**Installation notes:** University network blocks protonvpn.com DNS and port 53 outbound. Had to:
1. Use DNS-over-HTTPS via `https://1.1.1.1/dns-query` to resolve IPs
2. Hardcode IPs in `/etc/hosts`
3. Find correct RPM version (`1.0.3-1` not `1.0.1-2`) by browsing repo directory
4. Install with `sudo dnf install -y https://repo.protonvpn.com/fedora-43-stable/protonvpn-stable-release/protonvpn-stable-release-1.0.3-1.noarch.rpm`
5. Then `sudo dnf install -y proton-vpn-gnome-desktop`

---

### Browsers & Anonymity

#### Tor Browser
**What it is:** Browser that routes traffic through the Tor anonymity network, bouncing it through 3+ relays before reaching the destination. Makes traffic extremely difficult to trace.

**Access:** Desktop icon or terminal
```bash
torbrowser-launcher
```

**Use cases:**
- Anonymous browsing
- Accessing .onion sites
- Bypassing censorship
- Research without leaving a trail

**Installation:**
```bash
sudo dnf install -y tor torbrowser-launcher
```
First launch downloads the actual Tor Browser bundle automatically.

---

### Offensive Security Tools

#### Metasploit Framework
**What it is:** The industry-standard penetration testing framework. Contains hundreds of exploits, payloads, and auxiliary modules.

**Access:** Desktop icon (launches terminal) or:
```bash
msfconsole
```

**Use cases:**
- Exploit known vulnerabilities in target systems
- Generate payloads (reverse shells, meterpreter sessions)
- Post-exploitation (privilege escalation, lateral movement)
- Vulnerability scanning

**Common commands:**
```bash
msfconsole                    # launch
search <exploit name>         # find modules
use <module>                  # select module
set RHOSTS <target IP>        # set target
set PAYLOAD <payload>         # set payload
run / exploit                 # execute
```

#### Burp Suite Community
**What it is:** Web application security testing platform. Intercepts and manipulates HTTP/S traffic between browser and web server.

**Access:** Desktop icon or terminal
```bash
burpsuite
```

**Use cases:**
- Web app pentesting
- Intercept and modify HTTP requests
- Scan for SQLi, XSS, IDOR, and other web vulns
- Fuzz parameters
- Brute force login forms

#### Bettercap
**What it is:** Swiss army knife for network attacks and monitoring. Handles WiFi, BLE, HID, and Ethernet attacks.

**Access:** Terminal only
```bash
sudo bettercap
```

**Use cases:**
- ARP spoofing / MITM attacks
- Network sniffing
- WiFi deauth attacks
- Credential harvesting on local network
- BLE device scanning

**Installation notes:** Not in Fedora repos. Built from source with Go:
```bash
sudo dnf install -y golang libusb1-devel libnetfilter_queue-devel libpcap-devel
go install github.com/bettercap/bettercap@latest
echo 'export PATH=$PATH:$HOME/go/bin' >> ~/.zshrc
```

#### Nikto
**What it is:** Web server scanner that checks for dangerous files, outdated software, and misconfigurations.

**Access:** Terminal
```bash
nikto -h <target>
```

**Use cases:**
- Quick web server vulnerability scan
- Find exposed admin panels
- Detect default credentials
- Identify outdated software versions

#### SQLmap
**What it is:** Automated SQL injection tool. Detects and exploits SQL injection flaws in web applications.

**Access:** Terminal
```bash
sqlmap -u "http://target.com/page?id=1"
```

**Use cases:**
- Detect SQL injection vulnerabilities
- Extract database contents
- Dump usernames and passwords
- Bypass authentication

#### Hydra
**What it is:** Fast and flexible online password brute-forcing tool supporting 50+ protocols.

**Access:** Terminal
```bash
hydra -l admin -P /usr/share/seclists/Passwords/Common-Credentials/10-million-password-list-top-1000.txt ssh://target
```

**Use cases:**
- Brute force SSH, FTP, HTTP, RDP, and more
- Credential stuffing attacks
- Dictionary attacks against login forms

#### Gobuster / ffuf
**What it is:** Directory/file fuzzing tools that brute force URLs to find hidden content.

**Access:** Terminal
```bash
gobuster dir -u http://target.com -w /usr/share/seclists/Discovery/Web-Content/common.txt
ffuf -u http://target.com/FUZZ -w /usr/share/seclists/Discovery/Web-Content/common.txt
```

**Use cases:**
- Find hidden directories and files
- Enumerate subdomains
- Fuzz parameters
- Find admin panels

#### Proxychains
**What it is:** Forces any TCP connection to go through a proxy (SOCKS4, SOCKS5, HTTP). Chains multiple proxies together.

**Access:** Terminal — prepend to any command
```bash
proxychains nmap -sT target
proxychains curl http://target.com
```

**Config:** `/etc/proxychains.conf`

**Use cases:**
- Route tool traffic through Tor
- Chain multiple proxies for anonymity
- Bypass IP-based blocks

---

### WiFi & Wireless Auditing

#### Aircrack-ng Suite
**What it is:** Complete suite for WiFi security auditing. Includes tools for capturing, analyzing, and cracking WiFi traffic.

**Access:** Terminal
```bash
airmon-ng start wlan0          # enable monitor mode
airodump-ng wlan0mon           # capture packets
aircrack-ng capture.cap -w wordlist.txt  # crack
```

**Use cases:**
- WPA/WPA2 handshake capture
- Crack captured handshakes
- Deauthentication attacks
- Fake AP creation

#### Kismet
**What it is:** Wireless network detector, sniffer, and intrusion detection system. Passive — doesn't transmit.

**Access:** Terminal
```bash
sudo kismet
```
Then open browser at `http://localhost:2501`

**Use cases:**
- Passive WiFi network discovery
- Detect hidden SSIDs
- Monitor for rogue APs
- Bluetooth device detection
- Log all nearby wireless traffic

#### hcxdumptool + hcxtools
**What it is:** Tools for capturing and converting WiFi traffic for use with hashcat. More powerful than aircrack-ng for modern WPA3.

**Access:** Terminal
```bash
sudo hcxdumptool -i wlan0 -o capture.pcapng --active_beacon
hcxpcapngtool capture.pcapng -o hashes.hc22000
hashcat -m 22000 hashes.hc22000 wordlist.txt
```

**Use cases:**
- Capture WPA/WPA2/WPA3 handshakes
- PMKID attacks (no client needed)
- Convert captures for hashcat

**Installation notes:** Not in Fedora repos. Built from source:
```bash
git clone https://github.com/ZerBea/hcxdumptool.git
cd hcxdumptool && make && sudo make install
```

---

### Reverse Engineering & Forensics

#### Ghidra
**What it is:** NSA's open-source reverse engineering framework. Disassembles and decompiles binaries into readable code.

**Access:** Desktop icon or terminal
```bash
ghidra
```

**Use cases:**
- Analyze malware
- Reverse engineer binaries
- Find vulnerabilities in compiled software
- CTF challenges
- Firmware analysis

**Installation notes:**
- Downloaded release ZIP from https://github.com/NationalSecurityAgency/ghidra/releases
- Extracted to `/opt/ghidra_12.0.4_PUBLIC/`
- Requires Java 21 JDK: `sudo dnf install -y java-21-openjdk-devel`
- On first run, manually specify JDK path: `/usr/lib/jvm/java-21-openjdk-21.0.10.0.7-2.fc43.x86_64`
- Symlinked: `sudo ln -sf /opt/ghidra_12.0.4_PUBLIC/ghidraRun /usr/local/bin/ghidra`

#### Radare2
**What it is:** Open-source reverse engineering framework and binary analysis toolset. Terminal-based, extremely powerful.

**Access:** Terminal
```bash
r2 <binary>           # open binary
r2 -d <binary>        # open in debug mode
```

**Common r2 commands:**
```
aaa          # analyze all
pdf @ main   # disassemble main function
iz           # list strings
ii           # list imports
VV           # visual graph mode
```

**Use cases:**
- Binary analysis and disassembly
- Debugging
- Exploit development
- CTF challenges
- Malware analysis

#### Binwalk
**What it is:** Firmware analysis and extraction tool. Identifies and extracts embedded files and code from firmware images.

**Access:** Terminal
```bash
binwalk firmware.bin
binwalk -e firmware.bin    # extract
```

**Use cases:**
- IoT device firmware analysis
- Extract hidden files from images
- Find embedded filesystems
- Identify compression and encryption

#### ImHex
**What it is:** Feature-rich hex editor with pattern language, data visualization, and disassembler.

**Access:** Terminal or app launcher
```bash
imhex
```

**Use cases:**
- Analyze binary files
- Craft custom payloads
- Reverse engineer file formats
- USB Rubber Ducky payload crafting

#### Steghide
**What it is:** Steganography tool that hides data inside image and audio files.

**Access:** Terminal
```bash
steghide embed -cf image.jpg -sf secret.txt    # hide data
steghide extract -sf image.jpg                  # extract data
```

**Use cases:**
- Hide data inside images
- CTF steganography challenges
- Covert data exfiltration
- Detect hidden data in files

#### ExifTool
**What it is:** Reads, writes, and edits metadata in image, audio, video, and document files.

**Access:** Terminal
```bash
exiftool image.jpg          # read metadata
exiftool -all= image.jpg    # strip all metadata
```

**Use cases:**
- OSINT — extract GPS coordinates, device info from photos
- Strip metadata before sharing files
- Forensic investigation of files
- CTF challenges

---

### OSINT

#### Maltego
**What it is:** Visual link analysis and data mining tool. Maps relationships between people, organizations, domains, IPs, and more.

**Access:** Desktop icon or terminal
```bash
maltego
```

**Note:** Currently broken on Fedora 43 due to Java compatibility issues (requires Java 11/17, only 21/25 available). Use web version at maltego.com or run via Docker with older Java.

**Use cases:**
- Map relationships between entities
- Domain and IP intelligence
- Social media investigation
- Infrastructure mapping
- Phishing campaign research

#### theHarvester
**What it is:** OSINT tool for gathering emails, subdomains, IPs, and URLs from public sources.

**Access:** Terminal
```bash
theHarvester -d target.com -b google
theHarvester -d target.com -b all
```

**Use cases:**
- Reconnaissance on target organizations
- Find employee email addresses
- Discover subdomains
- Map attack surface before a pentest

**Installation:**
```bash
pip install theHarvester --break-system-packages
```

#### Sherlock
**What it is:** Hunts usernames across hundreds of social media platforms simultaneously.

**Access:** Terminal
```bash
sherlock username
sherlock username1 username2    # multiple targets
```

**Use cases:**
- Find all accounts associated with a username
- OSINT on individuals
- Investigate threat actors
- Verify your own digital footprint

**Installation:**
```bash
pip install sherlock-project --break-system-packages
```

---

### Password Cracking

#### Hashcat
**What it is:** World's fastest GPU-based password recovery tool. Supports 300+ hash types.

**Access:** Terminal
```bash
hashcat -m 0 hashes.txt wordlist.txt              # MD5
hashcat -m 1000 hashes.txt wordlist.txt           # NTLM
hashcat -m 22000 hashes.txt wordlist.txt          # WPA2
hashcat -m 0 hashes.txt -a 3 ?a?a?a?a?a?a        # brute force
```

**Common hash modes:**
| Mode | Type |
|------|------|
| 0 | MD5 |
| 100 | SHA1 |
| 1000 | NTLM |
| 1800 | SHA-512 Unix |
| 22000 | WPA2 |

**Use cases:**
- Crack captured WiFi handshakes
- Crack dumped password hashes
- Password auditing
- CTF challenges

**Note:** Running CPU-only mode (no NVIDIA/AMD GPU). Performance limited but functional.

#### John the Ripper
**What it is:** Classic open-source password cracker. Better than hashcat for some formats, especially Unix passwords and encrypted files.

**Access:** Terminal
```bash
john hashes.txt                          # auto-detect and crack
john --wordlist=wordlist.txt hashes.txt  # dictionary attack
john --show hashes.txt                   # show cracked passwords
```

**Use cases:**
- Crack Unix/Linux password hashes
- Crack zip, PDF, Office file passwords
- Crack SSH private key passphrases
- Password auditing

---

### Network Tools

#### Wireshark
**What it is:** The most widely-used network protocol analyzer. Captures and analyzes network traffic in real time.

**Access:** Desktop icon or terminal
```bash
wireshark
```

**Use cases:**
- Capture and analyze network traffic
- Debug network issues
- Detect suspicious traffic
- Analyze malware network behavior
- Extract credentials from unencrypted protocols

#### Nmap
**What it is:** The gold standard network scanner. Discovers hosts, open ports, services, and OS information.

**Access:** Terminal
```bash
nmap 192.168.1.1                    # basic scan
nmap -sV -sC 192.168.1.1           # service/version detection
nmap -A 192.168.1.0/24             # aggressive scan on subnet
nmap -p- 192.168.1.1               # all 65535 ports
```

**Use cases:**
- Network discovery
- Port scanning
- Service enumeration
- OS fingerprinting
- Pre-exploitation reconnaissance

#### Netcat
**What it is:** The "Swiss army knife" of networking. Creates TCP/UDP connections for data transfer, port scanning, and reverse shells.

**Access:** Terminal
```bash
nc -lvnp 4444                          # listen on port 4444
nc target 4444                         # connect to target
nc -lvnp 4444 > received_file         # receive file
```

**Use cases:**
- Set up reverse shell listeners
- Transfer files between machines
- Port scanning
- Banner grabbing
- Chat between machines

---

### AI & Local LLM

#### Ollama
**What it is:** Run large language models locally on your own hardware. No internet required, completely private.

**Access:** Terminal or via Open WebUI
```bash
ollama run llama3.2              # chat with llama3.2
ollama list                      # list installed models
ollama pull <model>              # download a model
ollama serve                     # start API server
```

**Installed models:** llama3.2 (3.2B parameters)

**API:** `http://localhost:11434`

**Use cases:**
- Private AI assistant with no data leaving your machine
- Code generation and review
- Security research assistance
- Offline AI when on restricted networks

**Installation:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
```

**Note:** Configured to listen on `0.0.0.0:11434` for Docker access:
```bash
# /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

#### Open WebUI
**What it is:** ChatGPT-style web interface for Ollama. Access your local LLMs through a browser UI.

**Access:** Open browser at `http://localhost:3000`

**Use cases:**
- Friendly GUI for local LLMs
- Chat history and conversation management
- Multiple model support
- System prompt customization

**Installation:** Runs as a Docker container
```bash
docker run -d \
  -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  -e OFFLINE_MODE=true \
  --name open-webui \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

**Persistence:** Container has `--restart always` — survives reboots automatically.

**Ollama connection:** Set API URL to `http://172.17.0.1:11434` in Admin Panel → Settings → Connections.

---

### Engineering & Hardware

#### Arduino IDE
**What it is:** Official IDE for programming Arduino microcontrollers and compatible boards.

**Access:** Desktop icon or terminal
```bash
/opt/arduino-ide.AppImage
```

**Use cases:**
- Program Arduino boards (Uno, Mega, Nano, etc.)
- Develop IoT devices
- Interface with sensors and actuators
- Prototype hardware projects
- Flash custom firmware

**Installation:** Downloaded AppImage from arduino.cc/en/software
```bash
chmod +x arduino-ide.AppImage
sudo mv arduino-ide.AppImage /opt/arduino-ide.AppImage
```

#### KiCad
**What it is:** Professional open-source PCB design suite. Used by hobbyists and professionals to design circuit boards.

**Access:** Desktop icon or terminal
```bash
kicad
```

**Includes:**
- Schematic editor (eeschema)
- PCB layout editor (pcbnew)
- Gerber viewer
- PCB calculator

**Use cases:**
- Design custom PCBs
- Create schematics
- Generate manufacturing files
- Design custom hardware implants or tools

#### Fritzing
**What it is:** Electronics design tool focused on prototyping. Great for breadboard diagrams and simple PCB design.

**Access:** Desktop icon or terminal
```bash
fritzing
```

**Use cases:**
- Visualize breadboard circuits
- Document hardware projects
- Simple PCB design
- Educational circuit diagrams

#### Minicom / Picocom
**What it is:** Serial terminal emulators for communicating with microcontrollers and embedded devices over UART.

**Access:** Terminal
```bash
sudo minicom -D /dev/ttyUSB0 -b 115200
sudo picocom /dev/ttyUSB0 -b 115200
```

**Use cases:**
- Serial console access to Arduino, ESP32, etc.
- Debug embedded devices
- Access router/switch console ports
- Communicate with IoT devices

---

### Privacy & System Tools

#### KeePassXC
**What it is:** Offline, open-source password manager. All passwords stored locally in an encrypted database.

**Access:** Desktop icon or terminal
```bash
keepassxc
```

**Use cases:**
- Store all passwords securely offline
- Generate strong random passwords
- Store SSH keys and notes
- No cloud sync — completely private

#### BleachBit
**What it is:** System cleaner and privacy tool. Securely deletes files and clears application data.

**Access:** Desktop icon or terminal
```bash
bleachbit
sudo bleachbit    # for system files
```

**Use cases:**
- Secure file deletion
- Clear browser history, cookies, cache
- Free up disk space
- Remove evidence of activity
- Wipe free space

#### Signal
**What it is:** End-to-end encrypted messaging app.

**Access:** Desktop icon

**Use cases:**
- Encrypted communications
- Secure messaging with contacts
- Encrypted voice/video calls

---

### Wordlists & Payloads

#### SecLists
**What it is:** The most comprehensive collection of security wordlists. Used with virtually every offensive tool.

**Location:** `/usr/share/seclists/`

**Contents:**
```
/usr/share/seclists/
├── Discovery/          # web content, DNS, subdomains
├── Fuzzing/            # fuzz strings, special chars
├── Passwords/          # password lists
├── Payloads/           # web app payloads
├── Pattern-Matching/   # grep patterns
├── Usernames/          # username lists
└── Miscellaneous/      # everything else
```

**Common usage:**
```bash
# Web directory fuzzing
gobuster dir -u http://target.com -w /usr/share/seclists/Discovery/Web-Content/common.txt

# Password attacks
hydra -l admin -P /usr/share/seclists/Passwords/Common-Credentials/10-million-password-list-top-1000.txt ssh://target

# Subdomain enumeration
gobuster dns -d target.com -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt
```

---

## Installation Notes & Gotchas

### University Network DNS Blocking
The university network (`spartans.ut`) blocks external DNS (port 53 outbound) and specifically blocks domains like `protonvpn.com`. Workaround used throughout:

```bash
# Use DNS-over-HTTPS to resolve IPs
curl -s "https://1.1.1.1/dns-query?name=example.com&type=A" -H "accept: application/dns-json"

# Hardcode resolved IPs in /etc/hosts
echo "IP_ADDRESS domain.com" | sudo tee -a /etc/hosts

# Clean up after install
sudo sed -i '/domain/d' /etc/hosts
```

### Ollama + Docker Networking
Ollama by default only listens on `localhost`. To allow Docker containers to reach it:

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

Open WebUI connects via `http://172.17.0.1:11434` (the docker0 bridge IP).

### Java Version Hell
- Ghidra requires Java 21 JDK (not just JRE): `sudo dnf install -y java-21-openjdk-devel`
- Maltego requires Java 11 or 17 — not available on Fedora 43. Currently broken.
- On first Ghidra launch, manually specify: `/usr/lib/jvm/java-21-openjdk-21.0.10.0.7-2.fc43.x86_64`

### Bettercap PATH
Go installs to `~/go/bin` which isn't in PATH by default:
```bash
echo 'export PATH=$PATH:$HOME/go/bin' >> ~/.zshrc
source ~/.zshrc
```

### ProtonVPN Repo Version
The documented version `1.0.1-2` returns 404. Correct version as of install:
```bash
# Browse repo to find current version
curl -sk https://repo.protonvpn.com/fedora-43-stable/protonvpn-stable-release/
# Install correct version
sudo dnf install -y https://repo.protonvpn.com/fedora-43-stable/protonvpn-stable-release/protonvpn-stable-release-1.0.3-1.noarch.rpm
```

### hcxdumptool
Not in Fedora repos, must build from source:
```bash
sudo dnf install -y gcc make libpcap-devel openssl-devel
git clone https://github.com/ZerBea/hcxdumptool.git
cd hcxdumptool && make && sudo make install
```
