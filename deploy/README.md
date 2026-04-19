# Deployment Assets

This directory contains host-level deployment files that are not copied into the backend Docker image.

## OpenClaw Gateway

`openclaw-gateway.service` is a systemd template for running OpenClaw on the backend VPS host.

Before installing it, update these fields for your server user and repo path:

```text
User=hive
WorkingDirectory=/home/hive/Hive_mind/Hive_mind/backend
HOME=/home/hive
OPENCLAW_STATE_DIR=/home/hive/.openclaw
```

Then install:

```bash
sudo cp deploy/openclaw-gateway.service /etc/systemd/system/openclaw-gateway.service
sudo systemctl daemon-reload
sudo systemctl enable --now openclaw-gateway
sudo systemctl status openclaw-gateway
```

