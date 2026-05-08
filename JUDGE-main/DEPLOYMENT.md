# JudgeTracker Atlas - Azure Deployment Guide

Deploy the application to Azure Container Apps with managed PostgreSQL.

## Prerequisites

- Azure subscription
- [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli) (>= 2.40)
- [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) (>= 1.5)
- Docker (for local image builds)

## Quick Start

1. **Login to Azure**
   ```bash
   az login
   azd auth login
   ```

2. **Initialize environment**
   ```bash
   azd init
   # Select 'Use code in the current directory'
   # Environment name: judgetracker-prod
   ```

3. **Set required secrets**
   ```bash
   azd env set AZURE_POSTGRES_ADMIN_PASSWORD "$(openssl rand -base64 32)"
   azd env set AZURE_JWT_SECRET "$(openssl rand -base64 32)"
   azd env set AZURE_ENABLE_ADMIN_REVIEW true
   azd env set AZURE_ENABLE_ADMIN_IMPORTS true
   ```

4. **Provision and deploy**
   ```bash
   azd up
   ```

## Manual Deployment Steps

### 1. Provision Infrastructure Only
```bash
azd provision
```

Creates:
- Resource group
- Container Registry
- Container Apps Environment
- PostgreSQL Flexible Server (with PostGIS)
- Backend Container App
- Frontend Container App

### 2. Build and Deploy Containers
```bash
azd deploy
```

Builds Docker images and pushes to Container Registry, then deploys to Container Apps.

### 3. Verify Deployment
```bash
./scripts/post-deploy.sh
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Azure                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │        Container Apps Environment               │    │
│  │  ┌──────────────┐    ┌──────────────────────┐  │    │
│  │  │  Frontend    │    │      Backend         │  │    │
│  │  │  (Next.js)   │───▶│     (FastAPI)        │  │    │
│  │  │  Port: 3000  │    │     Port: 8000       │  │    │
│  │  └──────────────┘    └──────────┬───────────┘  │    │
│  │                                   │              │    │
│  └───────────────────────────────────┼──────────────┘    │
│                                        │                  │
│  ┌─────────────────────────────────────▼──────────────┐   │
│  │      PostgreSQL Flexible Server                   │   │
│  │      (with PostGIS extension)                     │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AZURE_ENV_NAME` | Environment name (resource naming) | `judgetracker-prod` |
| `AZURE_LOCATION` | Azure region | `eastus` |
| `AZURE_POSTGRES_ADMIN_PASSWORD` | PostgreSQL admin password | Required |
| `AZURE_JWT_SECRET` | Secret for admin tokens | Required |
| `AZURE_ENABLE_ADMIN_REVIEW` | Enable review queue API | `true` |
| `AZURE_ENABLE_ADMIN_IMPORTS` | Enable import endpoints | `true` |

### Post-Deployment URLs

After `azd up`, the following URLs are available:
- **Frontend**: `https://ca-frontend-{env}.{region}.azurecontainerapps.io`
- **Backend API**: `https://ca-backend-{env}.{region}.azurecontainerapps.io`
- **API Docs**: `{backend}/docs`

## Database Migrations

Migrations run automatically on container startup via the entrypoint script (`alembic upgrade head`).

To run migrations manually:
```bash
# Get backend container app name
az containerapp exec --name ca-backend-{env} --resource-group rg-{env} --command "alembic upgrade head"
```

## Troubleshooting

### Container won't start
Check logs:
```bash
az containerapp logs show --name ca-backend-{env} --resource-group rg-{env} --follow
```

### Database connection issues
1. Verify PostgreSQL firewall allows Azure services
2. Check `JTA_DATABASE_URL` environment variable
3. Ensure PostGIS extension is enabled

### Build failures
Ensure Docker is running and you're logged in:
```bash
az acr login --name {registry-name}
```

## Cleanup

Remove all Azure resources:
```bash
azd down --purge
```

**Warning**: `--purge` permanently deletes data in PostgreSQL and Container Registry.

## Cost Estimates

| Component | Monthly Cost (approx) |
|-----------|----------------------|
| Container Apps (2 apps) | $15-30 |
| PostgreSQL B1ms | $13 |
| Container Registry (Basic) | $5 |
| Log Analytics | $2-5 |
| **Total** | **~$35-50** |

## Egress Proxy Configuration

All outbound ingestion fetches must route through an egress proxy that enforces
DNS rebinding protection (see `backend/app/ingestion/safe_fetch.py § DNS Rebinding`).
The backend **will refuse to start in production** unless one of the following is
satisfied:

### Option A — Application-level proxy (recommended)

Set `JTA_FETCH_EGRESS_PROXY` to an HTTP/HTTPS proxy URL:

```bash
azd env set JTA_FETCH_EGRESS_PROXY "http://squid-proxy.internal:3128"
```

All `safe_fetch` calls automatically honour this variable.

### Option B — Network/infrastructure-level policy

If your platform enforces egress at the network level (e.g., Azure Firewall +
User-Defined Routes, or a service mesh with sidecar proxy), set the
acknowledgement flag instead:

```bash
azd env set JTA_ALLOW_DIRECT_PROD_FETCH_WITH_NETWORK_POLICY "1"
```

This suppresses the startup guard but does **not** route traffic through a proxy.
You are responsible for ensuring the network policy actually enforces egress.

### Behaviour table

| `JTA_FETCH_EGRESS_PROXY` | `JTA_ALLOW_DIRECT_PROD_FETCH_WITH_NETWORK_POLICY` | Result |
|--------------------------|---------------------------------------------------|--------|
| set | any | Start succeeds, proxy used |
| unset | unset | **Start fails with exit 1** |
| unset | `1` | Start succeeds, no app-level proxy |

## Security Notes

- Admin tokens are stored as Container App secrets (encrypted)
- PostgreSQL uses Azure-managed credentials
- CORS is configured for cross-origin requests
- No persistent volumes (stateless containers)

## Support

For issues:
1. Check `azd show` for deployment status
2. Review Container App logs in Azure Portal
3. Verify PostgreSQL connectivity
