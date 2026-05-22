from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from .models import models  # noqa: F401 — registers all models
    Base.metadata.create_all(bind=engine)
    _run_migrations()


def _run_migrations():
    """Agrega columnas nuevas a tablas existentes (SQLite no soporta ALTER TABLE automático)."""
    from sqlalchemy import text, inspect
    insp = inspect(engine)
    with engine.connect() as conn:
        # tasks: fecha_inicio, fecha_vencimiento
        task_cols = {c["name"] for c in insp.get_columns("tasks")}
        if "fecha_inicio" not in task_cols:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN fecha_inicio DATE"))
        if "fecha_vencimiento" not in task_cols:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN fecha_vencimiento DATE"))
        # projects: fecha_inicio, responsable, specs_text
        proj_cols = {c["name"] for c in insp.get_columns("projects")}
        if "fecha_inicio" not in proj_cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN fecha_inicio DATE"))
        if "responsable" not in proj_cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN responsable VARCHAR(100)"))
        if "specs_text" not in proj_cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN specs_text TEXT"))
        if "links_json" not in proj_cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN links_json TEXT"))
        if "structure_text" not in proj_cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN structure_text TEXT"))
        if "structure_image_url" not in proj_cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN structure_image_url VARCHAR(500)"))
        if "archived" not in proj_cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN archived BOOLEAN DEFAULT 0 NOT NULL"))
        if "tarifa_hora" not in proj_cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN tarifa_hora FLOAT"))
        if "presupuesto" not in proj_cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN presupuesto FLOAT"))
        if "subtareas_json" not in task_cols:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN subtareas_json TEXT"))
        if "elapsed_seconds" not in task_cols:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN elapsed_seconds INTEGER DEFAULT 0 NOT NULL"))
        if "timer_started_at" not in task_cols:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN timer_started_at DATETIME"))
        if "task_type" not in task_cols:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN task_type VARCHAR(20) DEFAULT 'task' NOT NULL"))
        if "meeting_with" not in task_cols:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN meeting_with VARCHAR(200)"))
        if "meeting_prep_url" not in task_cols:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN meeting_prep_url VARCHAR(500)"))
        if "meeting_prep_filename" not in task_cols:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN meeting_prep_filename VARCHAR(200)"))
        # projects: google integration fields
        if "drive_folder_id" not in proj_cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN drive_folder_id VARCHAR(100)"))
        if "calendar_event_id" not in proj_cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN calendar_event_id VARCHAR(200)"))
        # tasks: calendar event id
        if "calendar_event_id" not in task_cols:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN calendar_event_id VARCHAR(200)"))
        # notifications table (creada por create_all, pero migración por si acaso)
        existing_tables = {t for t in insp.get_table_names()}
        if "notifications" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id VARCHAR PRIMARY KEY,
                    tipo VARCHAR(30) NOT NULL DEFAULT 'sistema',
                    titulo VARCHAR(200) NOT NULL,
                    mensaje TEXT,
                    project_id VARCHAR REFERENCES projects(id) ON DELETE CASCADE,
                    task_id VARCHAR,
                    leida BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
        conn.commit()
