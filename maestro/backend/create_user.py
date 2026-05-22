"""
Script de setup inicial — crea el primer usuario en la BD.

Uso:
    cd backend
    python create_user.py

    # Crear usuario con contraseña custom:
    python create_user.py --username alexis --password MiClave123 --display "Alexis Orsi"

    # Cambiar contraseña de un usuario existente:
    python create_user.py --username alexis --password NuevaClave --reset
"""

import argparse
import sys
import os

# Asegurar que el módulo app sea importable
sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine, SessionLocal, Base
from app.models.models import User
from app.security import hash_password


DEFAULT_USERNAME = "alexis"
DEFAULT_PASSWORD = "password123"
DEFAULT_DISPLAY  = "Alexis Orsi"


def create_user(username: str, password: str, display_name: str, email: str | None, reset: bool):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()

        if existing and not reset:
            print(f"✓ El usuario '{username}' ya existe. Usá --reset para cambiar la contraseña.")
            return

        if existing and reset:
            existing.hashed_password = hash_password(password)
            existing.is_active = True
            db.commit()
            print(f"✓ Contraseña de '{username}' actualizada correctamente.")
            return

        user = User(
            username=username,
            hashed_password=hash_password(password),
            display_name=display_name,
            email=email,
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"✓ Usuario '{username}' creado correctamente.")
        print(f"  Display name : {display_name}")
        print(f"  Email        : {email or '(sin email)'}")
        print()
        print("  Para iniciar sesión:")
        print(f"    Usuario   : {username}")
        print(f"    Contraseña: {password}")
        print()
        print("  IMPORTANTE: cambiá la contraseña en producción.")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Crear usuario inicial para MAESTRO")
    parser.add_argument("--username",  default=DEFAULT_USERNAME, help=f"Nombre de usuario (default: {DEFAULT_USERNAME})")
    parser.add_argument("--password",  default=DEFAULT_PASSWORD, help=f"Contraseña (default: {DEFAULT_PASSWORD})")
    parser.add_argument("--display",   default=DEFAULT_DISPLAY,  help=f"Nombre a mostrar (default: {DEFAULT_DISPLAY})")
    parser.add_argument("--email",     default=None,             help="Email (opcional)")
    parser.add_argument("--reset",     action="store_true",       help="Resetear contraseña si el usuario ya existe")
    args = parser.parse_args()

    if len(args.password) < 6:
        print("Error: la contraseña debe tener al menos 6 caracteres.", file=sys.stderr)
        sys.exit(1)

    create_user(args.username, args.password, args.display, args.email, args.reset)


if __name__ == "__main__":
    main()
