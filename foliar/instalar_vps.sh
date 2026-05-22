#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
#  Foliar — Script de instalación en VPS (Ubuntu 22.04)
#  Dominio: foliar-arrechea.duckdns.org
#
#  USO:
#    1. Conectarse al VPS por SSH:
#         ssh root@IP_DEL_VPS
#    2. Subir este script:
#         scp instalar_vps.sh root@IP_DEL_VPS:~
#    3. Ejecutar:
#         bash instalar_vps.sh
# ══════════════════════════════════════════════════════════════════════════════

set -e  # detener si hay error

DOMINIO="foliar-arrechea.duckdns.org"
APP_DIR="/home/ubuntu/foliar"
USER="ubuntu"

echo ""
echo "════════════════════════════════════════════"
echo "  Foliar — Instalación en VPS"
echo "  Dominio: $DOMINIO"
echo "════════════════════════════════════════════"
echo ""

# ── 1. Actualizar sistema e instalar dependencias ─────────────────────────────
echo "[1/8] Actualizando sistema..."
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx \
               tesseract-ocr tesseract-ocr-spa git unzip curl

# ── 2. Crear usuario ubuntu si no existe ──────────────────────────────────────
echo "[2/8] Preparando usuario..."
id -u $USER &>/dev/null || useradd -m -s /bin/bash $USER

# ── 3. Subir archivos del proyecto ────────────────────────────────────────────
echo "[3/8] Creando directorio del proyecto..."
mkdir -p $APP_DIR
chown -R $USER:$USER $APP_DIR

echo ""
echo "  ► Ahora subí los archivos del proyecto a $APP_DIR"
echo "    Desde tu PC local (en otra terminal):"
echo "    scp -r C:/Users/M01/Desktop/form_agent/* root@IP_DEL_VPS:$APP_DIR/"
echo ""
read -p "  Presioná ENTER cuando hayas subido los archivos..."

# ── 4. Entorno virtual Python ─────────────────────────────────────────────────
echo "[4/8] Instalando dependencias Python..."
cd $APP_DIR
sudo -u $USER python3 -m venv venv
sudo -u $USER venv/bin/pip install --upgrade pip
sudo -u $USER venv/bin/pip install -r requirements.txt
sudo -u $USER venv/bin/pip install gunicorn

# ── 5. Configurar variables de entorno ───────────────────────────────────────
echo "[5/8] Configurando .env..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp $APP_DIR/.env.example $APP_DIR/.env
    echo ""
    echo "  ► Editá el archivo .env con tus credenciales:"
    echo "    nano $APP_DIR/.env"
    echo ""
    echo "    Completá:"
    echo "    ANTHROPIC_API_KEY=sk-ant-api03-..."
    echo "    FLASK_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
    echo "    FOLIAR_ENV=production"
    echo ""
    read -p "  Presioná ENTER cuando hayas guardado el .env..."
fi
chmod 600 $APP_DIR/.env
chown $USER:$USER $APP_DIR/.env

# ── 6. Logs ────────────────────────────────────────────────────────────────────
echo "[6/8] Creando directorio de logs..."
mkdir -p /var/log/foliar
chown $USER:$USER /var/log/foliar

# ── 7. Nginx + SSL ────────────────────────────────────────────────────────────
echo "[7/8] Configurando Nginx..."
cat > /etc/nginx/sites-available/foliar << EOF
server {
    listen 80;
    server_name $DOMINIO;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name $DOMINIO;

    ssl_certificate     /etc/letsencrypt/live/$DOMINIO/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMINIO/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options SAMEORIGIN always;

    client_max_body_size 25M;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_read_timeout 200s;
    }

    location /api/stream/ {
        proxy_pass             http://127.0.0.1:8000;
        proxy_set_header       Host              \$host;
        proxy_set_header       X-Forwarded-Proto \$scheme;
        proxy_buffering        off;
        proxy_cache            off;
        proxy_read_timeout     300s;
        proxy_set_header       Connection        '';
        chunked_transfer_encoding on;
    }

    location /api/batch/stream/ {
        proxy_pass             http://127.0.0.1:8000;
        proxy_set_header       Host              \$host;
        proxy_set_header       X-Forwarded-Proto \$scheme;
        proxy_buffering        off;
        proxy_cache            off;
        proxy_read_timeout     600s;
        proxy_set_header       Connection        '';
        chunked_transfer_encoding on;
    }
}
EOF

ln -sf /etc/nginx/sites-available/foliar /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t

echo "  Obteniendo certificado SSL gratuito (Let's Encrypt)..."
certbot --nginx -d $DOMINIO --non-interactive --agree-tos -m admin@arrechea.com.ar
systemctl reload nginx

# ── 8. Servicio systemd ───────────────────────────────────────────────────────
echo "[8/8] Instalando servicio systemd..."
cat > /etc/systemd/system/foliar.service << EOF
[Unit]
Description=Foliar — Agente de formularios
After=network.target

[Service]
User=$USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn -c gunicorn.conf.py app:app
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=foliar

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable foliar
systemctl start foliar

# ── Verificación final ────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════"
echo "  ✅ Instalación completada"
echo ""
echo "  URL:  https://$DOMINIO"
echo ""
echo "  Comandos útiles:"
echo "    Ver logs:      journalctl -u foliar -f"
echo "    Reiniciar:     systemctl restart foliar"
echo "    Estado:        systemctl status foliar"
echo "════════════════════════════════════════════"
echo ""
