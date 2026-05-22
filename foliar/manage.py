"""
Foliar - Gestion de usuarios
Uso:
  python manage.py crear          -> crear un usuario nuevo
  python manage.py listar         -> ver todos los usuarios
  python manage.py borrar         -> borrar un usuario
  python manage.py cambiar-pass   -> cambiar contrasena de un usuario
"""
import sys
from app import app, db, User

def pedir_password(prompt):
    # input() normal: la contrasena se ve al escribir (herramienta local)
    return input(prompt).strip()

def crear_usuario():
    print("\n--- Crear usuario ---")
    username = input("  Usuario:     ").strip()
    email    = input("  Email:       ").strip().lower()
    while True:
        password = pedir_password("  Contrasena:  ")
        confirm  = pedir_password("  Confirmar:   ")
        if password == confirm:
            break
        print("  ERROR: Las contrasenias no coinciden, intenta de nuevo.")

    if len(password) < 8:
        print("  ERROR: La contrasena debe tener al menos 8 caracteres.")
        return

    with app.app_context():
        if User.query.filter_by(username=username).first():
            print(f"  ERROR: El usuario '{username}' ya existe.")
            return
        if User.query.filter_by(email=email).first():
            print(f"  ERROR: El email '{email}' ya esta registrado.")
            return
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"  OK: Usuario '{username}' creado correctamente.\n")

def listar_usuarios():
    with app.app_context():
        users = User.query.order_by(User.created_at).all()
        if not users:
            print("\n  No hay usuarios registrados.\n")
            return
        print(f"\n  {'ID':<5} {'Usuario':<20} {'Email':<30} {'Creado'}")
        print("  " + "-" * 70)
        for u in users:
            created = u.created_at.strftime("%d/%m/%Y %H:%M") if u.created_at else "-"
            print(f"  {u.id:<5} {u.username:<20} {u.email:<30} {created}")
        print()

def borrar_usuario():
    listar_usuarios()
    username = input("  Usuario a borrar: ").strip()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"  ERROR: No existe el usuario '{username}'.\n")
            return
        confirm = input(f"  Confirmas borrar a '{username}'? (s/n): ").strip().lower()
        if confirm == "s":
            db.session.delete(user)
            db.session.commit()
            print(f"  OK: Usuario '{username}' eliminado.\n")
        else:
            print("  Cancelado.\n")

def cambiar_password():
    listar_usuarios()
    username = input("  Usuario: ").strip()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"  ERROR: No existe el usuario '{username}'.\n")
            return
        while True:
            password = pedir_password("  Nueva contrasena:  ")
            confirm  = pedir_password("  Confirmar:         ")
            if password == confirm:
                break
            print("  ERROR: No coinciden, intenta de nuevo.")
        user.set_password(password)
        db.session.commit()
        print(f"  OK: Contrasena de '{username}' actualizada.\n")

COMANDOS = {
    "crear":        crear_usuario,
    "listar":       listar_usuarios,
    "borrar":       borrar_usuario,
    "cambiar-pass": cambiar_password,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    if cmd not in COMANDOS:
        print(__doc__)
        sys.exit(0)
    COMANDOS[cmd]()
