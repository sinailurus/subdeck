# SubDeck · Subscription Manager

[中文](README.md) ｜ English

A self-hosted subscription manager: track memberships, subscriptions and recurring bills, roll billing dates forward automatically, get due-date reminders, convert amounts with live exchange rates, and see weekly / monthly / yearly spending summaries.

> **AIGC notice:** This project was developed with AI assistance. Copyright and final decision authority belong to the repository owner.
>
> **Docs:** [User Agreement (TERMS.md)](TERMS.md) ｜ [Privacy policy](static/privacy-policy.html) (after deployment, available in-app at `http://NAS_IP:8300/assets/privacy-policy.html`)

## Features

- 📋 **Subscription management**: name, amount, currency, billing cycle (weekly / monthly / quarterly / semi-annually / yearly), payment method (auto-renewal / manual), category, notes
- 🔄 **Automatic billing-date rollover**: past billing dates roll forward to the next occurrence based on the cycle
- ⏰ **Upcoming payments**: subscriptions due soon enter a pending area with highlighting (lead time configurable)
- 💱 **Multi-currency + live rates**: 30 common currencies built in, rates synced automatically (based on European Central Bank reference rates); every amount can be converted to your preferred base currency
- 📊 **Spending statistics**: monthly / yearly totals, category breakdown (bar / donut / pie chart switch), timeline of charges in the next 30 days
- 🎨 **Appearance system**: custom theme color, three UI styles (solid / subtle glass / heavy glass), custom background image with adjustable overlay, custom app name and icon, all synced across devices
- 🖼️ **Logos**: built-in letter avatars with automatic colors, or upload your own images (PNG / JPG / WebP, up to 2MB)
- 📅 **Calendar feed**: one-click iCal link; billing dates appear in your phone's calendar app
- 📧 **Email reminders**: configure SMTP once and get an email before each charge (lead time configurable)
- 💾 **Data backup**: one-click full backup export / import from the web UI (with rollback), device migration without the command line
- 🌓 **Dark mode**: follows the system, or switch manually
- 📱 **Responsive layout**: desktop table + top navigation; phone / tablet cards + bottom navigation; installable to the home screen (PWA)
- 🔒 **Optional password**: enabled with one environment variable; HMAC-signed cookie + login rate limiting; safe to skip on a trusted LAN
- 🐳 **Single-container deployment**: SQLite storage, no external dependencies; backing up means copying one directory

## Quick start

### UGREEN UGOS Pro: app package (.upk)

Download the `.upk` matching your architecture from the [Releases](https://github.com/sinailurus/subdeck/releases) page (most x86 UGREEN models use `amd64`, ARM models use `arm64`) → install manually in the app center → follow the wizard to set an access password and a data folder. No Docker required.

> ⚠️ **This package is not yet listed in the UGREEN app store.** It is a developer-signed package and has not been reviewed by UGREEN. It is intended for users who have completed device authorization (App Center → Settings → App development settings) and accept the associated risk. Before installing, consider using the in-app "Data backup" feature to protect your data. Store progress will be announced in this repository's Releases.

### Windows / macOS one-click package (no NAS, no Docker)

Download the latest archive from the [Releases](https://github.com/sinailurus/subdeck/releases) page → extract → run (Windows: `SubDeck.exe`; macOS: `SubDeck`, allow it once under System Settings → Privacy & Security) → your browser opens automatically. The data directory, access password and port are configured in `subdeck.ini` inside the archive (with comments), see the included readme file. On macOS, pick the `apple-silicon` (M-series) or `intel` archive matching your chip.

### Prebuilt image (NAS / Docker users, recommended)

Use the official image published by CI, no local build needed. In `docker-compose.yml`, set:

```yaml
image: ghcr.io/sinailurus/subdeck:latest
```

If GHCR is slow or unreachable from mainland China, use the NJU mirror (same content, synced within about 10 minutes of each release):

```yaml
image: ghcr.nju.edu.cn/sinailurus/subdeck:latest
```

For production, pin a version (e.g. `ghcr.nju.edu.cn/sinailurus/subdeck:1.6.18`) instead of `latest`. Other settings are the same as "Build locally". UGREEN users can also use [compose.ugreen.yml](compose.ugreen.yml) with the `image:` line replaced as above (the .upk app package remains the recommended route).

### Build locally

```bash
git clone https://github.com/sinailurus/subdeck.git
cd subdeck
cp .env.example .env        # set AUTH_PASSWORD
docker compose up -d        # default port 8300
```

Open `http://NAS_IP:8300`.

> **NAS permission note (UGREEN / Synology, read this)**: keep `user: "0:0"` in the compose file. With plain Docker deployments, the entrypoint first repairs the ownership of `/data` as root (fixing bind-mount permission mismatches), then drops privileges for the service process. Inside the UGREEN UGOS Pro package (.upk), `RUN_AS_ROOT=1` makes the service run as root directly: data folders created by the UGOS wizard use a "permission bits 000 + ACL whitelist" model that is reapplied on every container rebuild, so a non-root user cannot write reliably (confirmed by on-device testing in v1.6.18). If the container starts as non-root with mismatched ownership, it fails with `PermissionError: '/data/logos'` and restarts repeatedly.

### UGREEN UGOS (Docker "Projects")

> The .upk app package above is the recommended route (no Docker, works right after install). The following is for users who prefer managing Compose themselves in "Projects".

1. Docker → **Projects** → create a project named `subdeck`
2. Paste [compose.ugreen.yml](compose.ugreen.yml) from the repository root into the Compose configuration, **changing only `AUTH_PASSWORD`**
3. After deployment, open `http://NAS_IP:8300`; if the folder already exists, choose "Use existing folder"

**UGREEN notes:**

- **Redeploy after config changes**: container configuration is fixed at creation; editing the Compose file does not apply automatically. Trigger "Redeploy" to rebuild the container, and verify that the container's "Created" timestamp has refreshed
- **Keep `user: "0:0"`**: do not remove this line when deploying, upgrading or rebuilding (see the permission note above)
- **Check data before deleting a project**: the data directory lives inside the project folder. Before deleting the project, confirm `data/` and its contents are safe in File Management

See "Upgrading" below.

### Synology DSM (Container Manager)

1. In **File Station**, create a `subdeck` folder on a shared folder and upload the project files
2. Open **Container Manager** → **Project** → **Create**
3. Name it `subdeck`, point the path to that folder, and select "Use existing docker-compose.yml"
4. Finish the wizard, wait for the image pull, then open `http://NAS_IP:8300`

> ARM-based Synology models should use the prebuilt image above; local builds are very slow on ARM.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `AUTH_PASSWORD` | empty | Access password; **empty = no login**. Always set one before exposing the instance to the internet (e.g. through a tunnel) |
| `TZ` | `Asia/Shanghai` | Time zone, affects the "today" boundary and billing-date rollover |
| `SUBDECK_PORT` | `8300` | Host port |
| `SUBDECK_DATA` | `./data` | Data directory (database + uploaded logos) |
| `PUID` / `PGID` | empty | Optional. Align data directory ownership (for sharing a data directory with other NAS containers); both must be set to take effect |
| `RUN_AS_ROOT` | empty | Run the service as root (skips privilege drop). Built into the UGREEN upk; plain Docker deployments **do not need it**; only data folders created by the UGOS wizard (permission bits 000 + ACL whitelist) require it |

## Data backup

### In-app backup (recommended)

Settings → "Data backup":

- **Export backup**: one-click zip download of everything (subscriptions, settings, uploaded images). Optionally include sensitive values such as SMTP credentials
- **Import backup**: overwrite-style restore; your current data is archived first and can be **rolled back** with one click
- Migration: export on the old instance → import on the new one, no command line needed

### Directory-level backup

All data lives in `data/` (SQLite database + uploaded images):

- **Backup**: stop the container and copy the whole `data/` directory (hot-copying is acceptable in SQLite WAL mode)
- **Restore**: put the backed-up `data/` back in place and restart the container
- **Migrate**: copy `data/` to the new machine and run `docker compose up -d`

## Upgrading

All data (database / login key / uploaded images) lives in the mounted `data/` directory; an upgrade replaces the program only, keeping your data and login state. **The one red line: never change the `volumes` mapping path in the compose file**; a different path means the new container cannot read your old data.

### Docker (prebuilt image)

```bash
docker compose pull && docker compose up -d
```

For local builds, run `git pull && docker compose up -d --build`.

- Since v1.1.0 the /data permission issue is fixed in the program itself: if you previously added `user: "0:0"` as a workaround, removing it is recommended (keeping it still works); use `PUID` / `PGID` when aligning ownership with other containers
- UGREEN UGOS users are the exception: keep `user: "0:0"` in the compose file; UGOS versions parse compose fields differently and keeping the line is safer

### UGREEN UGOS (Docker "Projects")

Either route works:

- One-click update in the project list (with the NJU mirror, new releases become visible within about 10 minutes)
- "Project → Edit": change the version tag at the end of `image` (e.g. `:1.6.18`), save, then confirm "Redeploy"

Verify either route the same way: the container's "Created" timestamp has refreshed, and the in-app "About" page shows the new version.

### UGREEN UGOS (.upk app package)

Download the new `.upk` from Releases and reinstall it in the app center (select the same data folder); your data is unaffected.

### Synology DSM

Pull the new image in the registry, then recreate the container with the same mounted directory.

## Calendar feed

Settings → copy the "Calendar subscription link" → add it as a subscribed calendar in your phone's calendar app. Upcoming charges then appear in your calendar automatically (next 12 months).

> The link embeds an access token, equivalent to a password; do not share it publicly. If you change the access password, regenerate the link.

## Exchange rates

- Coverage: 30 currencies in European Central Bank reference rates (CNY / USD / EUR / JPY / GBP / HKD / KRW and more)
- Source: [frankfurter.dev](https://frankfurter.dev) (free, no API key), original data from the European Central Bank
- When the primary source is unreachable, a fallback ([open.er-api.com](https://www.exchangerate-api.com), also free) is used automatically; no manual action needed
- Rates are cached locally; the last cache is used while offline
- If a rare currency cannot be converted, it is clearly marked as "not included" instead of being counted incorrectly

## Security notes

- Password login uses HMAC-signed cookies with constant-time comparison
- Uploads accept PNG / JPG / WebP only (validated by file header; **SVG is rejected** to prevent XSS), up to 2MB per file
- Data stays in a local volume and is never sent to third-party services (except the exchange rate API, which only receives currency codes, never your subscription data)

## Project structure

```
subdeck/
├── app/            # FastAPI backend
│   ├── main.py     # routes and business logic
│   ├── db.py       # SQLite data layer
│   ├── auth.py     # password login and signed cookies
│   ├── billing.py  # billing-date rollover and conversion
│   ├── rates.py    # exchange-rate sync and cache
│   ├── mailer.py   # email reminders
│   ├── backup.py   # backup export / import / rollback
│   ├── ical.py     # calendar export
│   └── currencies.py
├── static/         # frontend (vanilla JS, no build step)
├── run_exe.py      # launcher for the Windows/macOS package
├── ugreen/         # UGREEN UGOS Pro app package (.upk) build config
├── docker-entrypoint.sh   # entrypoint: fix data dir ownership / drop privileges / RUN_AS_ROOT switch
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/  # builds multi-arch images / one-click packages / UGOS app packages
```

## Development and testing

```bash
pip install -r requirements.txt
AUTH_PASSWORD=test123 DATA_DIR=./data uvicorn app.main:app --port 8017
# in another terminal, run the end-to-end tests
python3 tests/e2e.py
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the complete history, updated with every release; read the upgrade notes for your target version before upgrading.

## License

From v1.1.0 the project is licensed under [PolyForm Noncommercial 1.0.0](LICENSE):

- Personal use, self-hosting and **non-commercial modification** are free; distributions must keep the copyright and license notices (the license's built-in `Required Notice` chain points back to this repository)
- Any commercial use (integrating it into commercial products, resale, paid hosting, etc.) requires **prior written permission from the author**
- v1.0.0 and earlier remain MIT-licensed (license changes do not apply retroactively)

© 2026 sinailurus · source repository per `Required Notice`

## Disclaimer

This project is provided "as is", for personal subscription tracking only. Billing dates and amounts are subject to your providers' actual invoices; the author is not liable for missed or incorrect payments based on data in this tool.
