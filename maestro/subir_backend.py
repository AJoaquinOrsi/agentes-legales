import paramiko
import getpass
import os

VPS_HOST = "2.24.108.79"
VPS_PORT = 22
VPS_USER = "root"

LOCAL_BASE = os.path.dirname(os.path.abspath(__file__))

BACKEND_FILES = [
    ("backend/app/routers/projects.py", "/opt/maestro/backend/app/routers/projects.py"),
    ("backend/app/routers/whatsapp.py", "/opt/maestro/backend/app/routers/whatsapp.py"),
    ("backend/app/routers/google_router.py", "/opt/maestro/backend/app/routers/google_router.py"),
    ("backend/app/routers/auth.py", "/opt/maestro/backend/app/routers/auth.py"),
    ("backend/app/routers/notifications.py", "/opt/maestro/backend/app/routers/notifications.py"),
    ("backend/app/schemas/schemas.py", "/opt/maestro/backend/app/schemas/schemas.py"),
    ("backend/app/config.py", "/opt/maestro/backend/app/config.py"),
    ("backend/app/security.py", "/opt/maestro/backend/app/security.py"),
    ("backend/app/models/models.py", "/opt/maestro/backend/app/models/models.py"),
    ("backend/app/database.py", "/opt/maestro/backend/app/database.py"),
    ("backend/app/main.py", "/opt/maestro/backend/app/main.py"),
    ("backend/app/services/notification_service.py", "/opt/maestro/backend/app/services/notification_service.py"),
]

password = getpass.getpass(f"Contraseña para {VPS_USER}@{VPS_HOST}: ")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print(f"\nConectando a {VPS_HOST}...")
ssh.connect(VPS_HOST, port=VPS_PORT, username=VPS_USER, password=password)

sftp = ssh.open_sftp()

for local_rel, remote in BACKEND_FILES:
    local = os.path.join(LOCAL_BASE, local_rel)
    print(f"  Subiendo {local_rel}...", end=" ")
    sftp.put(local, remote)
    print("OK")

sftp.close()

# Reiniciar uvicorn
print("\nReiniciando uvicorn...")
stdin, stdout, stderr = ssh.exec_command(
    "kill $(ps aux | grep 'uvicorn backend.app.main' | grep -v grep | awk '{print $2}') 2>/dev/null ; sleep 1 ; "
    "cd /opt/maestro && nohup /opt/maestro/backend/venv/bin/uvicorn backend.app.main:app "
    "--host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 &"
)
stdout.channel.recv_exit_status()
print("Uvicorn reiniciado.")

ssh.close()
print("\n✓ Backend actualizado.")
