# RustDesk Integration Analysis for RentaMac

## Overview

RustDesk becomes the primary remote access method for clients. Each client gets access to an assigned Mac mini via RustDesk with our self-hosted server.

## Architecture

```
Client's Browser/App          Gateway (89.125.30.138)         Mac Mini
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   RustDesk       │────>│  hbbs (ID: 21116)    │<────│   RustDesk      │
│   Desktop App    │     │  hbbr (Relay: 21117) │     │   (headless)    │
│   or Web Client  │     │                      │     │                 │
└─────────────────┘     │  Backend API (8000)   │     │  sshd (reverse) │
                         │  PostgreSQL           │     │  User: client   │
                         └──────────────────────┘     └─────────────────┘
```

## 1. Provisioning Flow (Client pays → gets access)

### Step-by-step automation:

```
1. Client pays (ЮKassa / crypto)
2. Backend.webhook receives payment confirmation
3. Backend assigns Mac mini (find available node)
4. Backend generates unique RustDesk password (random 8-char)
5. Backend SSH to Mac → sets RustDesk permanent password via RustDesk CLI/config
6. Backend sends client email/message with:
   - RustDesk download link
   - Server settings (ID Server, Relay Server, Key) — pre-configured in download
   - RustDesk ID of assigned Mac
   - Temporary password
7. Client connects → starts working
```

### Pre-configured RustDesk (Zero-Config for Client)

Best UX: **Custom RustDesk client** with our server baked in.

Options:
- **RustDesk MSI/DMG custom build** — compile RustDesk with our server hardcoded
- **RustDesk portable config** — deploy a .exe/.dmg that auto-imports server settings
- **Web client** — RustDesk 1.2+ supports web browser access
- **Config file deployment** — provide a downloadable `.toml` config

For MVP: Provide download links + server settings on pay page. Client pastes 3 fields once.

## 2. Access Control & Security

### Password Management

```
┌─────────────────────────────────────────────────────┐
│                 Password Lifecycle                    │
│                                                      │
│  Mac available         Client pays      Rental ends  │
│  ──────────>           ─────────>       ────────>    │
│  password: ???         password: Ab3x!  password: ??? │
│  (random, unknown)     (sent to client) (rotated)     │
└─────────────────────────────────────────────────────┘
```

- **Before rental**: RustDesk password is random/unknown — no one can connect
- **During rental**: Unique password per client, known only to them
- **After rental**: Password rotated immediately — client loses access

### Network Isolation

Client has full macOS desktop. They COULD:
- ❌ Scan internal network (10.0.0.x) — but there's nothing else there
- ❌ Change RustDesk settings — need to lock this
- ❌ Install backdoors — mitigated by full cleanup between clients
- ❌ Access other Macs — each Mac is isolated, no cross-connections

**Mitigation:**
- `pf` firewall on Mac: block all outbound except to Gateway + Apple servers
- RustDesk settings: lock with password so client can't change server
- macOS restrictions: use MDM or profiles to restrict System Settings

### Admin Access

Admin (you) should ALWAYS be able to connect alongside client:
- RustDesk allows multiple simultaneous connections
- Admin can shadow/observe client sessions
- Useful for support and debugging

## 3. Billing Integration

### Webhook Flow

```
ЮKassa webhook → POST /api/webhooks/yookassa
                    ↓
                Verify payment signature
                    ↓
                Lookup order (plan + mac_assignment)
                    ↓
    ┌───────────────┴───────────────┐
    ↓                               ↓
Activate access                Extend access
(new client)                   (renewal)
    │                               │
    ├─ Generate password            ├─ Keep same password
    ├─ Set on Mac via SSH           ├─ Just update expiry
    ├─ Send credentials             │
    └─ Start timer                  └─ Update timer
```

### Plans & Access Duration

| Plan | Access Duration | Auto-renew | Notes |
|------|----------------|------------|-------|
| Monthly | 30 days | Yes | Password stays same on renewal |
| Annual | 365 days | Yes | Discounted rate |
| Daily | 24 hours | No | One-shot, password rotated after |
| Hourly | N hours | No | Billed per hour, password rotated after |

### Grace Period

- 24h before expiry: warn client via email/Telegram
- At expiry: disable access (change password)
- 7-day grace: keep client data, then full cleanup

## 4. De-provisioning (Rental ends → Clean Mac)

### Tier 1: Basic Cleanup (Fast, ~1 min)

```bash
# Kill RustDesk connection
pkill -9 rustdesk

# Clear user data
rm -rf ~/Downloads/*
rm -rf ~/Desktop/*
rm -rf ~/Documents/*
rm -rf ~/.Trash/*
rm -rf ~/Library/Caches/*
rm -rf ~/Library/Containers/*/Data/Library/Caches/*
rm -rf ~/Library/Safari/*
rm -rf ~/Library/Application\ Support/Google/Chrome/*
rm -rf ~/Library/Application\ Support/Firefox/Profiles/*

# Clear keychain (except system)
security delete-keychain login.keychain-db 2>/dev/null

# Clear SSH keys
rm -rf ~/.ssh/authorized_keys
rm -rf ~/.ssh/id_*

# Clear shell history
rm -f ~/.zsh_history ~/.bash_history
history -c 2>/dev/null

# Reset RustDesk password
# (set new random password via config)
```

### Tier 2: Full Reset (Thorough, ~5 min)

```bash
# Everything from Tier 1, PLUS:

# Remove installed apps (non-App Store)
brew list --formula | xargs brew uninstall --force 2>/dev/null
brew list --cask | xargs brew uninstall --force 2>/dev/null

# Remove all non-system apps
ls /Applications/ | grep -v -E "^(Safari|Mail|Maps|Photos|FaceTime|Calendar|Reminders|Notes|Music|Podcasts|TV|News|Stocks|Home|FaceTime|System|iMovie|GarageBand|TextEdit|Preview|Terminal|Automator|Calculator|Chess|Dictionary|Font Book|Image Capture|Stickies|VoiceMemos)" | while read app; do
  rm -rf "/Applications/$app"
done

# Clear all user accounts except default
# Delete the client user, create fresh one

# Reset LaunchAgents
rm -rf ~/Library/LaunchAgents/com.rentamac.* 2>/dev/null
# Re-add our tunnel agent
```

### Tier 3: APFS Snapshot Restore (Best, ~2 min

)
```bash
# Before first rental: take a snapshot of clean state
tmutil localsnapshot

# When rental ends: restore to clean snapshot
tmutil restore / path/to/snapshot
```

**Recommendation**: Use APFS Snapshots for production. Instant restore, guaranteed clean state.

## 5. Monitoring & Health Checks

### What to Monitor

| Metric | How | Threshold |
|--------|-----|-----------|
| Mac online/offline | RustDesk API or ping | Alert if >5min offline |
| RustDesk connected | hbbs logs | Alert if client can't connect |
| CPU/RAM usage | `top` via SSH | Alert if >90% for >10min |
| Disk space | `df -h` via SSH | Alert if >85% full |
| Active session | RustDesk | Track session count |

### Heartbeat

Mac sends heartbeat to Gateway every 60 seconds:
```bash
# Via LaunchAgent (cron equivalent on macOS)
curl -s http://89.125.30.138:8000/api/nodes/heartbeat \
  -H "Authorization: Bearer $NODE_TOKEN" \
  -d '{"node_id": "mac-001", "status": "online"}'
```

## 6. Edge Cases & Concerns

### Client Misuse
- **Mining crypto**: Monitor CPU usage, kill suspicious processes
- **Illegal downloads**: Acceptable use policy in ToS
- **Breaking macOS**: Revert with APFS snapshot
- **Changing RustDesk settings**: Lock with admin password

### Technical
- **macOS updates**: Disable auto-updates, admin controls when to update
- **RustDesk updates**: Keep client/server versions compatible
- **Network bandwidth**: Each active session uses ~2-10 Mbps
- **Sleep prevention**: `caffeinate` or `systemsetup -setcomputersleep Never`
- **Reconnection**: RustDesk auto-reconnects, but Mac sleep breaks it
- **Multiple displays**: RustDesk supports multi-monitor
- **File transfer**: RustDesk has built-in file transfer — can be disabled for security
- **Clipboard**: Can be disabled to prevent data leakage between clients

### Legal
- **ToS/Acceptable Use**: Clients must agree to terms before access
- **Data retention**: Don't keep client data after rental ends
- **Privacy**: No screen recording/screenshotting without consent (legal requirement)

## 7. Implementation Priority

### Phase 1 (MVP — Now)
1. ✅ RustDesk server running on Gateway
2. ✅ Mac connected and working
3. 🔲 Set permanent password on Mac via SSH
4. 🔲 Backend API endpoint to set/get RustDesk password
5. 🔲 Pay page shows RustDesk connection instructions after payment
6. 🔲 Basic cleanup script between clients

### Phase 2 (Production Ready)
7. 🔲 Custom RustDesk client with pre-configured server
8. 🔲 APFS snapshot-based cleanup
9. 🔲 Network firewall on Mac (pf rules)
10. 🔲 Monitoring & heartbeat
11. 🔲 Auto-provisioning via API (fully automated)

### Phase 3 (Scale)
12. 🔲 MDM profiles for macOS restrictions
13. 🔲 Multiple Macs management
14. 🔲 Admin dashboard with live session monitoring
15. 🔲 Client self-service portal (restart, file upload)
16. 🔲 Usage analytics & billing dashboard

## 8. Costs & Bandwidth

RustDesk self-hosted: **FREE** (open source)

Bandwidth per active session:
- Low quality: ~0.5 Mbps
- Medium: ~2 Mbps
- High: ~5-10 Mbps

10 concurrent clients ≈ 20-100 Mbps — Gateway needs sufficient bandwidth.

## Key Decision: Web Client vs Desktop App

**Web Client (browser)**: 
- ✅ No install needed — works in any browser
- ✅ Easiest for clients
- ❌ Lower performance
- ❌ Requires hbbs port 21118 exposed

**Desktop App**:
- ✅ Best performance
- ✅ Full keyboard shortcuts
- ❌ Client must install software

**Recommendation**: Support both. Web for quick access, Desktop for power users. Expose port 21118 for web client.