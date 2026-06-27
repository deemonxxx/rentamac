# RentaMac

macOS node rental platform with automated provisioning, WireGuard VPN, and payment processing.

## Architecture

```
Client → WireGuard VPN → Gateway (this server) → macOS Node (SSH)
```

- **Backend** — FastAPI async API with PostgreSQL
- **Frontend** — rentamac.ru (Russian) and rentamac.pro (English)
- **mac-node/** — Provisioning scripts for macOS machines
- **gateway/** — WireGuard gateway setup

## Quick Start

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your values

# Start services
docker-compose up -d

# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/health | Health check |
| GET | /api/nodes | List all nodes |
| GET | /api/nodes/stats | Node statistics |
| POST | /api/nodes | Create node |
| PATCH | /api/nodes/{id} | Update node |
| DELETE | /api/nodes/{id} | Delete node |
| POST | /api/nodes/{id}/reboot | Reboot node |
| GET | /api/clients | List clients |
| POST | /api/clients | Create client |
| POST | /api/clients/assign | Assign client to node |
| POST | /api/clients/{id}/deprovision | Remove client |
| POST | /api/webhook/yukassa | YooKassa webhook |
| POST | /api/webhook/crypto | Crypto payment webhook |

## Development

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## License

Proprietary