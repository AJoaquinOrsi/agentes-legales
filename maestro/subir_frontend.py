import paramiko
import getpass
import os

VPS_HOST = "2.24.108.79"
VPS_PORT = 22
VPS_USER = "root"
VPS_PATH = "/opt/maestro/frontend"

LOCAL_DIR = os.path.dirname(os.path.abspath(__file__)) + "/frontend"

FILES = [
    "dashboard.jsx",
    "app.jsx",
    "project-detail.jsx",
    "sections.jsx",
    "data.jsx",
    "index.html",
]


password = getpass.getpass(f"Contraseña para {VPS_USER}@{VPS_HOST}: ")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print(f"\nConectando a {VPS_HOST}...")
ssh.connect(VPS_HOST, port=VPS_PORT, username=VPS_USER, password=password)

sftp = ssh.open_sftp()

for filename in FILES:
    local = os.path.join(LOCAL_DIR, filename)
    remote = f"{VPS_PATH}/{filename}"
    print(f"  Subiendo {filename}...", end=" ")
    sftp.put(local, remote)
    print("OK")

sftp.close()
ssh.close()

print("\n✓ Todos los archivos subidos correctamente.")
print("Hacé un hard refresh en el browser (Ctrl+Shift+R).")
