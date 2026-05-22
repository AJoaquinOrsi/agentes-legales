// =====================================================================
// MAESTRO — New sections: Tareas, Calendario, Estadísticas, Asistente, Configuración
// =====================================================================
const { useState: useS, useMemo: useM, useEffect: useE, useRef: useR } = React;
const Ds = window.MAESTRO_DATA;
const Is = window.MAESTRO_ICONS;
const { ChatPanel } = window.MAESTRO_CHAT;

// =====================================================================
// TAREAS
// =====================================================================
function NewTaskModal({ projects, onClose, onSave }) {
  const [projectId, setProjectId] = useS(projects[0]?.id || "");
  const [taskName, setTaskName] = useS("");
  const [taskType, setTaskType] = useS("task");
  const [fechaInicio, setFechaInicio] = useS("");
  const [fechaVencimiento, setFechaVencimiento] = useS("");
  const [horaInicio, setHoraInicio] = useS("");
  const [horaFin, setHoraFin] = useS("");
  const [saving, setSaving] = useS(false);

  const inputStyle = { width: "100%", boxSizing: "border-box", padding: "8px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 14 };
  const labelStyle = { fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 };

  const isMeeting = taskType === "meeting";

  const submit = async (e) => {
    e.preventDefault();
    if (!taskName.trim() || !projectId) return;
    setSaving(true);
    // Para reuniones: agregar horario a la descripción si se completó
    let finalName = taskName.trim();
    if (isMeeting && (horaInicio || horaFin)) {
      const rango = horaInicio && horaFin ? `${horaInicio} - ${horaFin}` : horaInicio || horaFin;
      finalName = `${finalName} (${rango})`;
    }
    try {
      await onSave({
        projectId,
        taskName: finalName,
        taskType,
        fechaInicio: isMeeting ? null : (fechaInicio || null),
        fechaVencimiento: fechaVencimiento || null,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const placeholders = { task: "Ej: Testear integración AFIP", meeting: "Ej: Reunión con cliente", event: "Ej: Presentación de informe" };
  const btnLabel = isMeeting ? "Crear reunión" : taskType === "event" ? "Crear evento" : "Crear tarea";

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}
      onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: "var(--r-lg)", padding: 28, width: 440, maxWidth: "90vw" }}>
        <h2 style={{ margin: "0 0 20px", fontSize: 16, fontWeight: 600 }}>Nueva tarea</h2>
        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label style={labelStyle}>Tipo</label>
            <div style={{ display: "flex", gap: 6 }}>
              {[["task","Tarea"], ["meeting","Reunión"], ["event","Evento"]].map(([v, l]) => (
                <button key={v} type="button" onClick={() => setTaskType(v)}
                  style={{ flex: 1, padding: "7px 0", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: taskType === v ? "var(--accent)" : "var(--bg-base)", color: taskType === v ? "#fff" : "var(--text-primary)", fontWeight: taskType === v ? 600 : 400, fontSize: 13, cursor: "pointer", transition: "all .15s" }}>
                  {l}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label style={labelStyle}>Proyecto *</label>
            <select value={projectId} onChange={e => setProjectId(e.target.value)} required style={inputStyle}>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Descripción *</label>
            <input autoFocus value={taskName} onChange={e => setTaskName(e.target.value)} placeholder={placeholders[taskType]} required style={inputStyle} />
          </div>

          {isMeeting ? (
            /* ── Reunión: fecha + horario ─────────────────────────── */
            <div style={{ display: "flex", gap: 12 }}>
              <div style={{ flex: 2 }}>
                <label style={labelStyle}>Fecha de la reunión</label>
                <input type="date" value={fechaVencimiento} onChange={e => setFechaVencimiento(e.target.value)} style={inputStyle} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={labelStyle}>Hora inicio</label>
                <input type="time" value={horaInicio} onChange={e => setHoraInicio(e.target.value)} style={inputStyle} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={labelStyle}>Hora fin</label>
                <input type="time" value={horaFin} onChange={e => setHoraFin(e.target.value)} style={inputStyle} />
              </div>
            </div>
          ) : (
            /* ── Tarea / Evento: fecha inicio + vencimiento ─────────── */
            <div style={{ display: "flex", gap: 12 }}>
              <div style={{ flex: 1 }}>
                <label style={labelStyle}>Fecha de inicio</label>
                <input type="date" value={fechaInicio} onChange={e => setFechaInicio(e.target.value)} style={inputStyle} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={labelStyle}>{taskType === "event" ? "Fecha del evento" : "Fecha de vencimiento"}</label>
                <input type="date" value={fechaVencimiento} onChange={e => setFechaVencimiento(e.target.value)} style={inputStyle} />
              </div>
            </div>
          )}

          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 8 }}>
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={saving || !taskName.trim() || !projectId}>
              {saving ? "Guardando…" : btnLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function TareasSection({ projects, onOpenProject, onToggleTask, onAddTask }) {
  const [showModal, setShowModal] = useS(false);
  const [showFilterPanel, setShowFilterPanel] = useS(false);
  const filterRef = useR(null);

  // ── Filtros activos ──────────────────────────────────────────────────────
  const [fEstado, setFEstado] = useS("pendientes");   // all | pendientes | completadas
  const [fPrioridad, setFPrioridad] = useS("all");    // all | alta | media | baja
  const [fTipo, setFTipo] = useS("all");              // all | task | meeting | event
  const [fVence, setFVence] = useS("all");            // all | hoy | semana | vencidas | sin_fecha
  const [fProyecto, setFProyecto] = useS("all");      // all | project.id

  // Cerrar al click afuera
  useE(() => {
    const h = e => { if (filterRef.current && !filterRef.current.contains(e.target)) setShowFilterPanel(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const [editingTaskId, setEditingTaskId] = useS(null);
  const [editTaskDesc, setEditTaskDesc] = useS("");
  const [editTaskDate, setEditTaskDate] = useS("");
  const [editTaskDateStart, setEditTaskDateStart] = useS("");
  const [editTaskPriority, setEditTaskPriority] = useS("media");
  const [savingEdit, setSavingEdit] = useS(false);
  const [confirmDeleteTaskId, setConfirmDeleteTaskId] = useS(null);

  const startEdit = (t) => {
    setEditingTaskId(t.id);
    setEditTaskDesc(t.name || "");
    setEditTaskDate(t.fechaVencimiento || "");
    setEditTaskDateStart(t.fechaInicio || "");
    setEditTaskPriority(t.priority || "media");
  };

  const saveEdit = async (t) => {
    setSavingEdit(true);
    try {
      await Ds.API.updateTask(t.project.id, t.id, {
        descripcion: editTaskDesc.trim() || t.name,
        fecha_inicio: editTaskDateStart || null,
        fecha_vencimiento: editTaskDate || null,
        prioridad: editTaskPriority,
      });
      setEditingTaskId(null);
      window.dispatchEvent(new CustomEvent("maestro:reloadProject", { detail: { projectId: t.project.id } }));
    } catch(e) { alert("Error: " + e.message); }
    finally { setSavingEdit(false); }
  };

  const allTasks = useM(() => {
    const a = [];
    projects.forEach(p => {
      p.tasks.forEach(t => a.push({ ...t, project: p }));
    });
    return a;
  }, [projects]);
  const isEmpty = allTasks.length === 0;

  const todayISO = new Date().toISOString().slice(0, 10);
  const weekEndISO = (() => {
    const d = new Date();
    d.setDate(d.getDate() + (7 - d.getDay()));
    return d.toISOString().slice(0, 10);
  })();

  const filtered = useM(() => {
    let r = allTasks;
    if (fEstado === "pendientes") r = r.filter(t => !t.done);
    if (fEstado === "completadas") r = r.filter(t => t.done);
    if (fPrioridad !== "all") r = r.filter(t => t.priority === fPrioridad);
    if (fTipo !== "all") r = r.filter(t => (t.taskType || "task") === fTipo);
    if (fVence === "hoy") r = r.filter(t => !t.done && t.fechaVencimiento === todayISO);
    if (fVence === "semana") r = r.filter(t => !t.done && t.fechaVencimiento && t.fechaVencimiento >= todayISO && t.fechaVencimiento <= weekEndISO);
    if (fVence === "vencidas") r = r.filter(t => !t.done && t.fechaVencimiento && t.fechaVencimiento < todayISO);
    if (fVence === "sin_fecha") r = r.filter(t => !t.fechaVencimiento);
    if (fProyecto !== "all") r = r.filter(t => t.project.id === fProyecto);
    return r;
  }, [allTasks, fEstado, fPrioridad, fTipo, fVence, fProyecto, todayISO, weekEndISO]);

  const activeFilterCount = [
    fEstado !== "pendientes", fPrioridad !== "all", fTipo !== "all",
    fVence !== "all", fProyecto !== "all"
  ].filter(Boolean).length;

  const resetFilters = () => { setFEstado("pendientes"); setFPrioridad("all"); setFTipo("all"); setFVence("all"); setFProyecto("all"); };

  const counts = {
    all: allTasks.length,
    pendientes: allTasks.filter(t => !t.done).length,
    completadas: allTasks.filter(t => t.done).length,
  };

  // Group by project
  const grouped = useM(() => {
    const g = {};
    filtered.forEach(t => {
      if (!g[t.project.id]) g[t.project.id] = { project: t.project, tasks: [] };
      g[t.project.id].tasks.push(t);
    });
    return Object.values(g);
  }, [filtered]);

  return (
    <section className="section">
      {showModal && projects.length > 0 && (
        <NewTaskModal projects={projects} onClose={() => setShowModal(false)} onSave={onAddTask} />
      )}
      <div className="section-head">
        <div>
          <div className="section-eyebrow">Tareas</div>
          <h1 className="section-title">Todas las tareas</h1>
          <p className="section-subtitle">
            {isEmpty
              ? "Las tareas aparecen acá cuando las agregás a un proyecto"
              : `${counts.pendientes} pendientes · ${counts.completadas} completadas · ${counts.all} totales`}
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => projects.length > 0 ? setShowModal(true) : null}
          title={projects.length === 0 ? "Primero creá un proyecto" : ""}>
          {Is.task(14)} Nueva tarea
        </button>
      </div>

      {isEmpty ? (
        <div className="empty-hero">
          <div className="empty-hero-mark">{Is.task(28)}</div>
          <h2>Sin tareas todavía</h2>
          <p>
            Las tareas se crean dentro de cada proyecto.<br />
            Decile al asistente «creá una tarea en {"<proyecto>"}» o usá el botón de arriba.
          </p>
          <div className="empty-hero-hints">
            <span className="empty-hint-chip">«creá una tarea: Testear integración»</span>
            <span className="empty-hint-chip">«mostrame las tareas de hoy»</span>
          </div>
        </div>
      ) : (
        <>
      {/* ── Barra de filtros ──────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        {/* Chips rápidos estado */}
        <button className={`filter-chip ${fEstado === "pendientes" ? "active" : ""}`} onClick={() => setFEstado("pendientes")}>
          Pendientes <span className="count">{counts.pendientes}</span>
        </button>
        <button className={`filter-chip ${fEstado === "completadas" ? "active" : ""}`} onClick={() => setFEstado("completadas")}>
          Completadas <span className="count">{counts.completadas}</span>
        </button>
        <button className={`filter-chip ${fEstado === "all" ? "active" : ""}`} onClick={() => setFEstado("all")}>
          Todas <span className="count">{counts.all}</span>
        </button>

        <div style={{ width: 1, height: 22, background: "var(--border)" }} />

        {/* Botón panel de filtros avanzados */}
        <div style={{ position: "relative" }} ref={filterRef}>
          <button
            className={`filter-chip ${activeFilterCount > 0 ? "active" : ""}`}
            onClick={() => setShowFilterPanel(v => !v)}
            style={{ gap: 6 }}>
            ⚙ Filtros{activeFilterCount > 0 && <span className="count">{activeFilterCount}</span>}
            <span style={{ fontSize: 9, opacity: 0.7 }}>{showFilterPanel ? "▲" : "▼"}</span>
          </button>
          {activeFilterCount > 0 && (
            <button onClick={resetFilters} style={{ position: "absolute", top: -6, right: -6, width: 16, height: 16, borderRadius: "50%", background: "var(--danger)", color: "#fff", fontSize: 9, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center", border: "none", cursor: "pointer", zIndex: 1 }}>✕</button>
          )}

          {/* Panel desplegable */}
          {showFilterPanel && (
            <div style={{ position: "absolute", top: "calc(100% + 8px)", left: 0, zIndex: 9999, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: "var(--r-lg)", boxShadow: "var(--shadow-lg)", padding: 18, width: 340, display: "flex", flexDirection: "column", gap: 16 }}>

              {/* Prioridad */}
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--fg-subtle)", marginBottom: 8 }}>Prioridad</div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {[["all","Todas"],["alta","Alta 🔴"],["media","Media 🟡"],["baja","Baja 🟢"]].map(([v,l]) => (
                    <button key={v} onClick={() => setFPrioridad(v)}
                      style={{ padding: "5px 12px", borderRadius: 99, fontSize: 12, fontWeight: 500, border: "1px solid var(--border)", cursor: "pointer", background: fPrioridad === v ? "var(--accent)" : "var(--bg-surface-2)", color: fPrioridad === v ? "#fff" : "var(--fg-muted)" }}>
                      {l}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tipo */}
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--fg-subtle)", marginBottom: 8 }}>Tipo de tarea</div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {[["all","Todas"],["task","Tarea"],["meeting","Reunión"],["event","Evento"]].map(([v,l]) => (
                    <button key={v} onClick={() => setFTipo(v)}
                      style={{ padding: "5px 12px", borderRadius: 99, fontSize: 12, fontWeight: 500, border: "1px solid var(--border)", cursor: "pointer", background: fTipo === v ? "var(--accent)" : "var(--bg-surface-2)", color: fTipo === v ? "#fff" : "var(--fg-muted)" }}>
                      {l}
                    </button>
                  ))}
                </div>
              </div>

              {/* Vencimiento */}
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--fg-subtle)", marginBottom: 8 }}>Vencimiento</div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {[["all","Todas"],["hoy","Hoy"],["semana","Esta semana"],["vencidas","Vencidas"],["sin_fecha","Sin fecha"]].map(([v,l]) => (
                    <button key={v} onClick={() => setFVence(v)}
                      style={{ padding: "5px 12px", borderRadius: 99, fontSize: 12, fontWeight: 500, border: "1px solid var(--border)", cursor: "pointer", background: fVence === v ? "var(--accent)" : "var(--bg-surface-2)", color: fVence === v ? "#fff" : "var(--fg-muted)" }}>
                      {l}
                    </button>
                  ))}
                </div>
              </div>

              {/* Proyecto */}
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--fg-subtle)", marginBottom: 8 }}>Proyecto</div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  <button onClick={() => setFProyecto("all")}
                    style={{ padding: "5px 12px", borderRadius: 99, fontSize: 12, fontWeight: 500, border: "1px solid var(--border)", cursor: "pointer", background: fProyecto === "all" ? "var(--accent)" : "var(--bg-surface-2)", color: fProyecto === "all" ? "#fff" : "var(--fg-muted)" }}>
                    Todos
                  </button>
                  {projects.map(p => (
                    <button key={p.id} onClick={() => setFProyecto(p.id)}
                      style={{ padding: "5px 12px", borderRadius: 99, fontSize: 12, fontWeight: 500, border: "1px solid var(--border)", cursor: "pointer", background: fProyecto === p.id ? "var(--accent)" : "var(--bg-surface-2)", color: fProyecto === p.id ? "#fff" : "var(--fg-muted)" }}>
                      {p.name}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <span style={{ fontSize: 12, color: "var(--fg-subtle)" }}>{filtered.length} resultado{filtered.length !== 1 ? "s" : ""}</span>
                <button onClick={() => { resetFilters(); setShowFilterPanel(false); }}
                  style={{ fontSize: 12, color: "var(--danger)", background: "none", border: "none", cursor: "pointer", fontWeight: 500 }}>
                  Limpiar filtros
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Tags de filtros activos */}
        {fPrioridad !== "all" && <span className="filter-chip active" style={{ fontSize: 11, height: 26 }}>Prioridad: {fPrioridad} <span onClick={() => setFPrioridad("all")} style={{ cursor: "pointer", marginLeft: 4 }}>✕</span></span>}
        {fTipo !== "all" && <span className="filter-chip active" style={{ fontSize: 11, height: 26 }}>Tipo: {fTipo} <span onClick={() => setFTipo("all")} style={{ cursor: "pointer", marginLeft: 4 }}>✕</span></span>}
        {fVence !== "all" && <span className="filter-chip active" style={{ fontSize: 11, height: 26 }}>Vence: {fVence} <span onClick={() => setFVence("all")} style={{ cursor: "pointer", marginLeft: 4 }}>✕</span></span>}
        {fProyecto !== "all" && <span className="filter-chip active" style={{ fontSize: 11, height: 26 }}>{projects.find(p=>p.id===fProyecto)?.name} <span onClick={() => setFProyecto("all")} style={{ cursor: "pointer", marginLeft: 4 }}>✕</span></span>}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {grouped.map(({ project, tasks }) => (
          <div key={project.id}>
            <div className="task-group-head">
              {project.blocked && <span className="pcard-blocker" />}
              <span className="task-group-name">{project.name}</span>
              <span className="col-count">{tasks.length}</span>
              <span style={{ flex: 1, height: 1, background: "var(--border)" }} />
              <span className="card-title-meta" style={{ cursor: "pointer" }} onClick={() => onOpenProject(project.id)}>
                Abrir proyecto →
              </span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {tasks.map(t => (
                <div key={t.id} style={{ borderRadius: "var(--r-md)", border: "1px solid var(--border)", background: "var(--bg-surface)", overflow: "hidden" }}>
                  <div className="task-card" style={{ border: "none", borderRadius: 0 }} onClick={() => onOpenProject(project.id)}>
                    <div className={`check-box ${t.done ? "done" : ""}`}
                      onClick={(e) => { e.stopPropagation(); onToggleTask(project.id, t.id); }}>
                      {t.done && Is.check(12)}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className={`t-name ${t.done ? "done" : ""}`}>{t.name}</div>
                      <div style={{ fontSize: 11, color: "var(--fg-muted)", marginTop: 2, fontFamily: "var(--font-mono)", display: "flex", gap: 10, flexWrap: "wrap" }}>
                        <span>{t.hours > 0 ? `${t.hours}h trabajadas` : "sin iniciar"} · {t.estimated || "?"}h est.</span>
                        {t.fechaInicio && <span style={{ color: "var(--accent)" }}>▶ {t.fechaInicio}</span>}
                        {t.fechaVencimiento && (
                          <span style={{ color: new Date(t.fechaVencimiento) < new Date() && !t.done ? "var(--danger)" : "var(--warning)" }}>
                            ⏱ vence {t.fechaVencimiento}
                          </span>
                        )}
                      </div>
                    </div>
                    <span className={`pcard-priority priority-${project.priority}`}>{project.priority}</span>
                    <span className="chip">{Ds.STATE_LABEL_SHORT[project.state]}</span>
                    {!t.done && (
                      <button className="btn btn-ghost" style={{ height: 26, fontSize: 12, padding: "0 8px", flexShrink: 0 }}
                        title="Editar tarea"
                        onClick={e => { e.stopPropagation(); editingTaskId === t.id ? setEditingTaskId(null) : startEdit(t); }}>
                        ✏️
                      </button>
                    )}
                    {confirmDeleteTaskId === t.id
                      ? <button className="btn btn-ghost" style={{ height: 26, fontSize: 12, padding: "0 8px", flexShrink: 0, color: "var(--danger)", border: "1px solid var(--danger)", fontWeight: 700 }}
                          onClick={async e => {
                            e.stopPropagation();
                            setConfirmDeleteTaskId(null);
                            try {
                              await Ds.API.deleteTask(t.project.id, t.id);
                              window.dispatchEvent(new CustomEvent("maestro:reloadProjects"));
                            } catch(err) { alert("Error al eliminar: " + err.message); }
                          }}>
                          ¿Seguro?
                        </button>
                      : <button className="btn btn-ghost" style={{ height: 26, fontSize: 12, padding: "0 8px", flexShrink: 0, color: "var(--danger)" }}
                          title="Eliminar tarea"
                          onClick={e => { e.stopPropagation(); setConfirmDeleteTaskId(t.id); setTimeout(() => setConfirmDeleteTaskId(null), 3000); }}>
                          🗑️
                        </button>
                    }
                    <span style={{ color: "var(--fg-subtle)" }}>{Is.arrowRight(14)}</span>
                  </div>
                  {editingTaskId === t.id && (
                    <div style={{ borderTop: "1px solid var(--accent)", padding: "12px 16px", background: "var(--bg-base)" }}
                      onClick={e => e.stopPropagation()}>
                      <div style={{ fontSize: 11, color: "var(--accent)", marginBottom: 8, fontWeight: 700, textTransform: "uppercase" }}>Editar tarea</div>
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        <input value={editTaskDesc} onChange={e => setEditTaskDesc(e.target.value)}
                          placeholder="Descripción"
                          style={{ padding: "6px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-surface)", color: "var(--text-primary)", fontSize: 13 }} />
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                          <div style={{ display: "flex", flexDirection: "column", gap: 3, flex: 1 }}>
                            <label style={{ fontSize: 11, color: "var(--fg-subtle)" }}>Fecha inicio</label>
                            <input type="date" value={editTaskDateStart} onChange={e => setEditTaskDateStart(e.target.value)}
                              style={{ padding: "6px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-surface)", color: "var(--text-primary)", fontSize: 13 }} />
                          </div>
                          <div style={{ display: "flex", flexDirection: "column", gap: 3, flex: 1 }}>
                            <label style={{ fontSize: 11, color: "var(--fg-subtle)" }}>Fecha vencimiento</label>
                            <input type="date" value={editTaskDate} onChange={e => setEditTaskDate(e.target.value)}
                              style={{ padding: "6px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-surface)", color: "var(--text-primary)", fontSize: 13 }} />
                          </div>
                          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                            <label style={{ fontSize: 11, color: "var(--fg-subtle)" }}>Prioridad</label>
                            <select value={editTaskPriority} onChange={e => setEditTaskPriority(e.target.value)}
                              style={{ padding: "6px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-surface)", color: "var(--text-primary)", fontSize: 13 }}>
                              <option value="alta">Alta</option>
                              <option value="media">Media</option>
                              <option value="baja">Baja</option>
                            </select>
                          </div>
                        </div>
                        {editTaskDate && <div style={{ fontSize: 11, color: "var(--fg-subtle)" }}>💡 Se sincronizará automáticamente con Google Calendar</div>}
                        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                          <button className="btn btn-ghost" style={{ height: 28, fontSize: 12 }} onClick={() => setEditingTaskId(null)}>Cancelar</button>
                          <button className="btn btn-primary" style={{ height: 28, fontSize: 12 }} disabled={savingEdit} onClick={() => saveEdit(t)}>
                            {savingEdit ? "Guardando..." : "Guardar"}
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="section-empty">Sin tareas que coincidan con este filtro</div>
        )}
      </div>
        </>
      )}
    </section>
  );
}

// =====================================================================
// CALENDARIO
// =====================================================================
function CalendarioSection({ projects, onOpenProject, onSyncCalendar }) {
  const now = new Date();
  const [view, setView] = useS({ month: now.getMonth(), year: now.getFullYear() });
  const [googleEvents, setGoogleEvents] = useS([]);
  const [googleLoading, setGoogleLoading] = useS(false);
  const [googleEnabled, setGoogleEnabled] = useS(false);

  useE(() => {
    Ds.API.googleStatus().then(s => {
      setGoogleEnabled(s.enabled);
      if (s.enabled) {
        setGoogleLoading(true);
        Ds.API.googleCalendarUpcoming(90).then(evs => {
          setGoogleEvents(evs);
        }).catch(() => {}).finally(() => setGoogleLoading(false));
      }
    }).catch(() => {});
  }, []);

  const todayISO = now.toISOString().slice(0, 10);
  const todayD = now.getDate(), todayM = now.getMonth(), todayY = now.getFullYear();

  // Parse ISO date string "YYYY-MM-DD" → { day, month, year } or null
  function parseISO(s) {
    if (!s || s === "—") return null;
    const [y, m, d] = s.split("-").map(Number);
    if (!y || !m || !d) return null;
    return { day: d, month: m - 1, year: y };
  }

  // Build events from projects and tasks
  const events = useM(() => {
    const ev = [];
    projects.forEach(p => {
      // Project start date
      const start = parseISO(p.fechaInicio);
      if (start) ev.push({ ...start, type: "inicio", text: `Inicio · ${p.name}`, projectId: p.id });
      // Project deadline
      const dl = parseISO(p.deadline);
      if (dl) ev.push({ ...dl, type: "deadline", text: `Vence · ${p.name}`, projectId: p.id });
      // Tasks
      (p.tasks || []).forEach(t => {
        const tStart = parseISO(t.fechaInicio);
        if (tStart) ev.push({ ...tStart, type: "tarea", text: `▶ ${t.name || t.descripcion} (${p.name})`, projectId: p.id, taskId: t.id });
        const tEnd = parseISO(t.fechaVencimiento);
        if (tEnd) ev.push({ ...tEnd, type: "vencimiento", text: `⏱ ${t.name || t.descripcion} (${p.name})`, projectId: p.id, taskId: t.id });
      });
    });
    return ev;
  }, [projects]);

  const DOW = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
  const MONTHS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

  const cells = useM(() => {
    const first = new Date(view.year, view.month, 1);
    let firstDow = (first.getDay() + 6) % 7;
    const daysInMonth = new Date(view.year, view.month + 1, 0).getDate();
    const prevDays = new Date(view.year, view.month, 0).getDate();
    const out = [];
    for (let i = firstDow - 1; i >= 0; i--) out.push({ d: prevDays - i, outside: true, m: view.month - 1, y: view.year });
    for (let d = 1; d <= daysInMonth; d++) out.push({ d, outside: false, m: view.month, y: view.year });
    while (out.length < 42) out.push({ d: out.length - daysInMonth - firstDow + 1, outside: true, m: view.month + 1, y: view.year });
    return out;
  }, [view]);

  // Parsear eventos de Google Calendar para el mes actual (definido ANTES de eventsByDay)
  const googleEventsForMonth = useM(() => {
    return (googleEvents || []).map(e => {
      const d = parseISO(e.fecha ? e.fecha.slice(0, 10) : "");
      if (!d) return null;
      return { ...d, type: "google", text: (e.titulo || "").replace("[MAESTRO] ", ""), link: e.link, id: e.id };
    }).filter(Boolean);
  }, [googleEvents]);

  const eventsByDay = useM(() => {
    const map = {};
    const allEvents = [
      ...(events || []),
      ...(googleEventsForMonth || []),
    ];
    allEvents.filter(e => e.month === view.month && e.year === view.year).forEach(e => {
      if (!map[e.day]) map[e.day] = [];
      map[e.day].push(e);
    });
    return map;
  }, [events, googleEventsForMonth, view]);

  const isToday = (d, m, y) => d === todayD && m === todayM && y === todayY;

  const goMonth = (delta) => {
    let m = view.month + delta, y = view.year;
    if (m < 0) { m = 11; y--; }
    if (m > 11) { m = 0; y++; }
    setView({ month: m, year: y });
  };

  const upcoming = useM(() => {
    return events
      .filter(e => {
        const d = new Date(e.year, e.month, e.day);
        return d >= new Date(todayY, todayM, todayD);
      })
      .sort((a, b) => new Date(a.year, a.month, a.day) - new Date(b.year, b.month, b.day))
      .slice(0, 8);
  }, [events]);

  const typeColor = {
    deadline: "var(--danger)",
    vencimiento: "var(--danger)",
    inicio: "var(--success)",
    tarea: "var(--accent)",
    meeting: "var(--warning)",
    google: "var(--fg-subtle)",
    note: "var(--warning)",
  };


  return (
    <section className="section">
      <div className="section-head">
        <div>
          <div className="section-eyebrow">Calendario</div>
          <h1 className="section-title">{MONTHS[view.month]} {view.year}</h1>
          <p className="section-subtitle">{events.filter(e => e.month === view.month && e.year === view.year).length} eventos este mes · fechas de proyectos y tareas</p>
        </div>
        <div className="cal-nav">
          {onSyncCalendar && (
            <button className="btn btn-ghost" style={{ height: 36, fontSize: 12, gap: 6 }} onClick={onSyncCalendar} title="Sincronizar con Google Calendar">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
              Google Cal
            </button>
          )}
          <button className="btn btn-ghost btn-icon" onClick={() => goMonth(-1)}>
            <span style={{ transform: "rotate(180deg)", display: "grid", placeItems: "center" }}>{Is.arrowRight(14)}</span>
          </button>
          <button className="btn btn-ghost" style={{ height: 36, fontSize: 12 }} onClick={() => setView({ month: todayM, year: todayY })}>Hoy</button>
          <button className="btn btn-ghost btn-icon" onClick={() => goMonth(1)}>{Is.arrowRight(14)}</button>
        </div>
      </div>

      <div className="cal-legend">
        <span className="cal-legend-item"><span className="cal-legend-dot" style={{ background: "var(--success)" }} /> Inicio proyecto</span>
        <span className="cal-legend-item"><span className="cal-legend-dot" style={{ background: "var(--danger)" }} /> Vencimiento</span>
        <span className="cal-legend-item"><span className="cal-legend-dot" style={{ background: "var(--accent)" }} /> Fecha tarea</span>
      </div>

      <div className="cal-grid">
        {DOW.map(d => <div key={d} className="cal-dow">{d}</div>)}
        {cells.map((c, i) => {
          const evs = c.outside ? [] : (eventsByDay[c.d] || []);
          return (
            <div key={i} className={`cal-day ${c.outside ? "outside" : ""} ${isToday(c.d, c.m, c.y) ? "today" : ""}`}>
              <div className="cal-day-num">{c.d}</div>
              {evs.slice(0, 3).map((e, ix) => (
                <div key={ix} className="cal-event"
                  style={{ background: typeColor[e.type] + "22", borderLeft: `2px solid ${typeColor[e.type]}`, color: "var(--text-primary)", cursor: e.projectId ? "pointer" : "default" }}
                  onClick={() => e.projectId && onOpenProject(e.projectId)}
                  title={e.text}>
                  {e.text}
                </div>
              ))}
              {evs.length > 3 && <div style={{ fontSize: 10, color: "var(--fg-muted)" }}>+{evs.length - 3} más</div>}
            </div>
          );
        })}
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <h3 className="card-title">Próximos eventos</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {upcoming.map((e, i) => (
            <div key={i} className="up-row" onClick={() => e.projectId && onOpenProject(e.projectId)} style={{ cursor: e.projectId ? "pointer" : "default" }}>
              <div className="up-date">
                <div className="up-date-d">{e.day}</div>
                <div className="up-date-m">{MONTHS[e.month].slice(0, 3)}</div>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{e.text}</div>
              </div>
              <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 10, background: (typeColor[e.type] || "var(--accent)") + "22", color: typeColor[e.type] || "var(--accent)" }}>{e.type}</span>
            </div>
          ))}
          {upcoming.length === 0 && (
            <div className="section-empty" style={{ padding: 24 }}>Sin eventos próximos — agregá fechas a tus proyectos y tareas</div>
          )}
        </div>
      </div>

      {googleEnabled && (
        <div className="card" style={{ marginTop: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
            <h3 className="card-title" style={{ margin: 0 }}>📅 Google Calendar</h3>
            {googleLoading && <span style={{ fontSize: 11, color: "var(--fg-subtle)" }}>Cargando...</span>}
            <button className="btn btn-ghost" style={{ marginLeft: "auto", height: 28, fontSize: 11 }}
              onClick={() => {
                setGoogleLoading(true);
                Ds.API.googleCalendarUpcoming(90).then(evs => setGoogleEvents(evs)).catch(() => {}).finally(() => setGoogleLoading(false));
              }}>
              ↻ Actualizar
            </button>
          </div>
          {googleEvents.length === 0 && !googleLoading ? (
            <div style={{ fontSize: 13, color: "var(--fg-subtle)", fontStyle: "italic" }}>Sin eventos [MAESTRO] en Google Calendar en los próximos 90 días.</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {googleEvents.map((e, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderRadius: "var(--r-md)", background: "var(--bg-base)", border: "1px solid var(--border)" }}>
                  <div style={{ minWidth: 40, textAlign: "center" }}>
                    <div style={{ fontSize: 16, fontWeight: 700, lineHeight: 1 }}>{e.fecha ? new Date(e.fecha + "T12:00:00").getDate() : "—"}</div>
                    <div style={{ fontSize: 10, color: "var(--fg-subtle)" }}>{e.fecha ? MONTHS[new Date(e.fecha + "T12:00:00").getMonth()].slice(0, 3) : ""}</div>
                  </div>
                  <div style={{ flex: 1, fontSize: 13 }}>{e.titulo.replace("[MAESTRO] ", "")}</div>
                  {e.link && <a href={e.link} target="_blank" rel="noopener noreferrer" style={{ fontSize: 11, color: "var(--accent)" }}>Ver →</a>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

// =====================================================================
// ESTADÍSTICAS
// =====================================================================
function StatsSection({ projects, onRequestInsights }) {
  const isEmpty = projects.length === 0;
  const totalHours = projects.reduce((s, p) => s + p.actualHours, 0);
  const totalEstimated = projects.reduce((s, p) => s + p.estimatedHours, 0);
  const efficiency = totalHours > 0 ? (totalEstimated / totalHours) * 100 : 0;
  const totalProjects = projects.length;
  const blocked = projects.filter(p => p.blocked).length;
  const [insightsRequested, setInsightsRequested] = useS(false);

  // Pie data: by state
  const byState = useM(() => {
    const counts = {};
    Ds.STATES.forEach(s => counts[s] = 0);
    projects.forEach(p => counts[p.state]++);
    return Ds.STATES.map(s => ({ state: s, count: counts[s] }));
  }, [projects]);

  // Bar data: hours per project sorted desc
  const sortedByHours = useM(() => [...projects].sort((a, b) => b.actualHours - a.actualHours).slice(0, 7), [projects]);
  const maxBar = Math.max(...sortedByHours.map(p => Math.max(p.actualHours, p.estimatedHours)));

  // Real velocity: group rawHours by week (last 4 weeks), compute avg h/day
  const { velocityData, velocityLabels } = useM(() => {
    const now = new Date();
    const weeks = [0, 1, 2, 3].map(wk => {
      const start = new Date(now);
      start.setDate(now.getDate() - now.getDay() - wk * 7);
      start.setHours(0, 0, 0, 0);
      const end = new Date(start);
      end.setDate(start.getDate() + 6);
      const startISO = start.toISOString().slice(0, 10);
      const endISO = end.toISOString().slice(0, 10);
      let total = 0;
      let days = new Set();
      projects.forEach(p => {
        (p.rawHours || []).forEach(h => {
          if (h.fecha >= startISO && h.fecha <= endISO) {
            total += h.horas;
            days.add(h.fecha);
          }
        });
      });
      const avgPerDay = days.size > 0 ? total / days.size : 0;
      const label = wk === 0 ? "Esta sem." : `s -${wk}`;
      return { avg: parseFloat(avgPerDay.toFixed(1)), label };
    }).reverse();
    return { velocityData: weeks.map(w => w.avg), velocityLabels: weeks.map(w => w.label) };
  }, [projects]);

  // Donut SVG
  const total = byState.reduce((s, x) => s + x.count, 0);
  let acc = 0;
  const stateColors = {
    analisis: "oklch(0.7 0.14 235)",
    desarrollo: "oklch(0.55 0.20 280)",
    testing: "oklch(0.74 0.16 75)",
    listo: "oklch(0.62 0.15 158)",
    produccion: "oklch(0.5 0.10 270)",
  };
  const slices = byState.map(({ state, count }, i) => {
    const startPct = total ? acc / total : 0;
    acc += count;
    const endPct = total ? acc / total : 0;
    return { state, count, startPct, endPct, color: stateColors[state] };
  });
  const r1 = 60, r2 = 90;
  const cx = 95, cy = 95;
  const polar = (pct, r) => {
    const a = pct * Math.PI * 2 - Math.PI / 2;
    return [cx + Math.cos(a) * r, cy + Math.sin(a) * r];
  };
  const arc = (s) => {
    if (s.count === 0) return null;
    const [x1, y1] = polar(s.startPct, r2);
    const [x2, y2] = polar(s.endPct, r2);
    const [x3, y3] = polar(s.endPct, r1);
    const [x4, y4] = polar(s.startPct, r1);
    const large = s.endPct - s.startPct > 0.5 ? 1 : 0;
    return `M ${x1} ${y1} A ${r2} ${r2} 0 ${large} 1 ${x2} ${y2} L ${x3} ${y3} A ${r1} ${r1} 0 ${large} 0 ${x4} ${y4} Z`;
  };

  // Line chart for velocity
  const lcW = 360, lcH = 180, lcPadL = 40, lcPadR = 20, lcPadT = 16, lcPadB = 28;
  const lcMaxY = Math.max(Math.max(...velocityData) * 1.2, 1);
  const lcPath = velocityData.map((v, i) => {
    const x = lcPadL + (i / (velocityData.length - 1)) * (lcW - lcPadL - lcPadR);
    const y = lcPadT + (1 - v / lcMaxY) * (lcH - lcPadT - lcPadB);
    return `${i === 0 ? "M" : "L"} ${x} ${y}`;
  }).join(" ");

  return (
    <section className="section">
      <div className="section-head">
        <div>
          <div className="section-eyebrow">Estadísticas</div>
          <h1 className="section-title">Tu performance</h1>
          <p className="section-subtitle">{isEmpty ? "Cargá proyectos y registrá horas para ver tu performance" : "Mayo 2026 · datos sincronizados hace 2 min"}</p>
        </div>
      </div>

      <div className="summary-grid">
        <KPI label="Horas totales" icon={Is.clock(14)} value={isEmpty ? "0" : totalHours.toFixed(1)} unit="h" delta={`${totalEstimated}h estimadas`} />
        <KPI label="Eficiencia" icon={Is.bolt(14)} value={isEmpty ? "—" : efficiency.toFixed(0)} unit={isEmpty ? "" : "%"} delta={isEmpty ? "sin datos" : (efficiency < 100 ? "sobrestimás" : "subestimás")} deltaDir={isEmpty ? "" : (efficiency < 100 ? "up" : "down")} />
        <KPI label="Proyectos" icon={Is.folder(14)} value={String(totalProjects)} delta={`${blocked} bloqueados`} deltaDir={blocked > 0 ? "down" : ""} />
        <KPI label="Tasa completado" icon={Is.check(14)}
          value={isEmpty ? "—" : (() => {
            const allT = projects.flatMap(p => p.tasks);
            return allT.length > 0 ? Math.round(allT.filter(t => t.done).length / allT.length * 100) : 0;
          })()}
          unit={isEmpty ? "" : "%"}
          delta={isEmpty ? "sin tareas" : (() => {
            const allT = projects.flatMap(p => p.tasks);
            return `${allT.filter(t => t.done).length}/${allT.length} tareas`;
          })()} />
        <KPI label="Velocity sem." icon={Is.trend(14)}
          value={isEmpty ? "—" : (velocityData[velocityData.length - 1] || 0).toFixed(1)}
          unit={isEmpty ? "" : "h/d"}
          delta={(() => {
            if (isEmpty) return "sin datos";
            const curr = velocityData[velocityData.length - 1] || 0;
            const prev = velocityData[velocityData.length - 2] || 0;
            if (prev === 0) return "primera semana";
            const pct = Math.round(((curr - prev) / prev) * 100);
            return `${pct > 0 ? "+" : ""}${pct}% vs sem. pasada`;
          })()}
          deltaDir={(() => {
            if (isEmpty) return "";
            const curr = velocityData[velocityData.length - 1] || 0;
            const prev = velocityData[velocityData.length - 2] || 0;
            return curr >= prev ? "up" : "down";
          })()} />
      </div>

      {isEmpty ? (
        <div className="empty-hero">
          <div className="empty-hero-mark">{Is.trend(28)}</div>
          <h2>Sin datos para graficar</h2>
          <p>
            Las estadísticas aparecen cuando hay proyectos y horas registradas.<br />
            Vas a ver: distribución por estado, horas reales vs estimado,<br />
            tu velocity semanal y los insights del agente.
          </p>
        </div>
      ) : (
      <div className="stats-grid">
        <div className="card">
          <h3 className="card-title">
            Horas por proyecto
            <span className="card-title-meta">real vs estimado</span>
          </h3>
          <div className="bar-chart">
            {sortedByHours.map(p => {
              const ratio = p.actualHours / p.estimatedHours;
              const overEst = ratio > 1.1;
              const realPct = (p.actualHours / maxBar) * 100;
              const estPct = (p.estimatedHours / maxBar) * 100;
              return (
                <div key={p.id} className="bar-row">
                  <span className="bar-name">{p.name}</span>
                  <div className="bar-track">
                    <div className={`bar-fill ${overEst ? "over" : ""}`} style={{ width: `${realPct}%` }} />
                    <div className="bar-est" style={{ left: `${estPct}%` }} />
                  </div>
                  <span className="bar-val">{p.actualHours}h / {p.estimatedHours}h</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="card">
          <h3 className="card-title">Distribución por estado</h3>
          <div className="donut-wrap">
            <svg width="190" height="190" viewBox="0 0 190 190">
              {slices.map(s => arc(s) && (
                <path key={s.state} d={arc(s)} fill={s.color} opacity="0.95" />
              ))}
              <text x="95" y="92" textAnchor="middle" fontFamily="var(--font-display)" fontSize="32" fontWeight="600" fill="var(--fg)">{total}</text>
              <text x="95" y="110" textAnchor="middle" fontSize="11" fill="var(--fg-muted)">proyectos</text>
            </svg>
            <div className="donut-legend">
              {slices.map(s => (
                <div key={s.state} className="donut-leg-row">
                  <span className="leg-dot" style={{ background: s.color }} />
                  <span>{Ds.STATE_LABEL_SHORT[s.state]}</span>
                  <span className="leg-val">{s.count} · {total ? Math.round((s.count / total) * 100) : 0}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="card" style={{ gridColumn: "1 / -1" }}>
          <h3 className="card-title">
            Velocity semanal
            <span className="card-title-meta">horas/día promedio · últimas 4 semanas</span>
          </h3>
          {velocityData.every(v => v === 0) ? (
            <div style={{ height: 160, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--fg-subtle)", fontSize: 13, fontStyle: "italic" }}>
              Sin datos de horas — registrá horas en tus proyectos para ver la velocity
            </div>
          ) : (
            <div style={{ display: "flex", gap: 12, alignItems: "flex-end", height: 180, padding: "0 8px 0 0" }}>
              {/* Y axis labels */}
              <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", height: 140, paddingBottom: 28, flexShrink: 0 }}>
                {[lcMaxY, lcMaxY * 0.5, 0].map((v, i) => (
                  <div key={i} style={{ fontSize: 10, color: "var(--fg-muted)", fontFamily: "var(--font-mono)", textAlign: "right", lineHeight: 1 }}>
                    {v.toFixed(1)}
                  </div>
                ))}
              </div>
              {/* Bars */}
              {velocityData.map((v, i) => {
                const pct = lcMaxY > 0 ? (v / lcMaxY) * 100 : 0;
                return (
                  <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6, height: "100%" }}>
                    <div style={{ flex: 1, width: "100%", display: "flex", flexDirection: "column", justifyContent: "flex-end", position: "relative" }}>
                      {/* gridlines */}
                      {[0, 0.25, 0.5, 0.75, 1].map(t => (
                        <div key={t} style={{ position: "absolute", left: 0, right: 0, bottom: `${t * 100}%`, borderTop: "1px dashed var(--border)", opacity: 0.4 }} />
                      ))}
                      <div style={{ fontWeight: 600, fontSize: 11, color: "var(--accent)", textAlign: "center", marginBottom: 4, fontFamily: "var(--font-mono)" }}>{v}</div>
                      <div style={{
                        width: "70%", margin: "0 auto",
                        height: `${Math.max(pct, v > 0 ? 2 : 0)}%`,
                        minHeight: v > 0 ? 4 : 0,
                        background: "var(--accent)",
                        borderRadius: "4px 4px 0 0",
                        opacity: 0.85,
                        transition: "height 300ms ease",
                      }} />
                    </div>
                    <div style={{ fontSize: 11, color: "var(--fg-muted)", whiteSpace: "nowrap", paddingBottom: 2 }}>{velocityLabels[i]}</div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="card" style={{ gridColumn: "1 / -1" }}>
          <h3 className="card-title">
            Actividad reciente
            <span className="card-title-meta">todos los proyectos</span>
          </h3>
          {(() => {
            const allEvents = projects.flatMap(p =>
              (p.history || []).map(h => ({ ...h, projectName: p.name, projectId: p.id }))
            ).sort((a, b) => (b.ts || 0) - (a.ts || 0)).slice(0, 15);
            if (allEvents.length === 0) return (
              <div style={{ padding: "16px 0", textAlign: "center", color: "var(--fg-subtle)", fontSize: 13 }}>Sin actividad registrada todavía</div>
            );
            const typeColors = { state: "var(--accent)", hours: "var(--success)", time: "var(--success)", task: "var(--accent)", note: "var(--warning)", blocker: "var(--danger)" };
            return (
              <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
                {allEvents.map((h, i) => (
                  <div key={i} style={{ display: "flex", gap: 12, padding: "8px 0", borderBottom: i < allEvents.length - 1 ? "1px solid var(--border)" : "none", alignItems: "center" }}>
                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: typeColors[h.type] || "var(--fg-subtle)", flexShrink: 0 }} />
                    <div style={{ fontSize: 11, color: "var(--fg-muted)", minWidth: 80, fontFamily: "monospace" }}>{h.time}</div>
                    <div style={{ fontSize: 12, fontWeight: 500, color: "var(--accent)", minWidth: 100, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{h.projectName}</div>
                    <div style={{ flex: 1, fontSize: 13, color: "var(--text-primary)" }}>{h.text}</div>
                  </div>
                ))}
              </div>
            );
          })()}
        </div>

        <div className="card" style={{ gridColumn: "1 / -1" }}>
          <h3 className="card-title">
            Insights del agente
            {onRequestInsights && (
              <button className="btn btn-ghost" style={{ height: 28, fontSize: 12, marginLeft: "auto" }}
                onClick={() => { setInsightsRequested(true); onRequestInsights(); }}>
                {Is.sparkles(12)} Solicitar análisis IA
              </button>
            )}
          </h3>
          {insightsRequested ? (
            <div style={{ padding: "20px 0", textAlign: "center", color: "var(--fg-muted)", fontSize: 13 }}>
              {Is.sparkles(16)}
              <div style={{ marginTop: 8 }}>Análisis solicitado al asistente — revisá la pestaña Asistente</div>
            </div>
          ) : (
            <div style={{ padding: "20px 0", textAlign: "center", color: "var(--fg-subtle)", fontSize: 13 }}>
              Hacé clic en "Solicitar análisis IA" para que el asistente analice tu performance y te dé recomendaciones personalizadas.
            </div>
          )}
        </div>
      </div>
      )}
    </section>
  );
}

function InsightRow({ color, text }) {
  return (
    <div style={{
      padding: "12px 14px",
      borderRadius: "var(--r-md)",
      background: `var(--${color}-soft)`,
      borderLeft: `3px solid var(--${color})`,
      fontSize: 13,
      display: "flex",
      alignItems: "flex-start",
      gap: 10,
    }}>
      <span style={{ color: `var(--${color})`, marginTop: 1 }}>
        {color === "danger" ? Is.alert(14) : color === "warning" ? Is.fire(14) : color === "info" ? Is.bolt(14) : Is.check(14)}
      </span>
      <span>{text}</span>
    </div>
  );
}

function KPI({ label, icon, value, unit, delta, deltaDir }) {
  return (
    <div className="kpi">
      <div className="kpi-label">
        <span className="kpi-icon">{icon}</span>
        <span>{label}</span>
      </div>
      <div>
        <span className="kpi-value mono">{value}</span>
        {unit && <span className="kpi-unit">{unit}</span>}
      </div>
      {delta && (
        <div className={`kpi-delta ${deltaDir || ""}`}>
          {deltaDir === "up" ? Is.trend(12) : deltaDir === "down" ? Is.trendDown(12) : null}
          <span>{delta}</span>
        </div>
      )}
    </div>
  );
}

// =====================================================================
// ASISTENTE (full-width chat)
// =====================================================================
function AsistenteSection({ messages, onSend, onConfirm, onOpenProject, onNewConversation, sessions = [], onLoadSession, onDeleteSession, currentSessionId }) {
  const [deleteConfirm, setDeleteConfirm] = useS(null);

  const fmtTime = (iso) => {
    if (!iso) return "";
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now - d;
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffDays === 0) return "hoy";
    if (diffDays === 1) return "ayer";
    if (diffDays < 7) return `${diffDays}d`;
    return d.toLocaleDateString("es-AR", { day: "numeric", month: "short" });
  };

  const handleDelete = (e, id) => {
    e.stopPropagation();
    if (deleteConfirm === id) {
      onDeleteSession && onDeleteSession(id);
      setDeleteConfirm(null);
    } else {
      setDeleteConfirm(id);
    }
  };

  return (
    <div className="assistant-shell">
      <aside className="assistant-side">
        <button className="btn btn-primary" style={{ height: 36, fontSize: 13 }} onClick={onNewConversation}>
          {Is.sparkles(14)} Nueva conversación
        </button>
        <h4>Historial</h4>
        {sessions.length === 0 && (
          <div style={{ padding: 14, fontSize: 11.5, color: "var(--fg-subtle)", textAlign: "center", marginTop: 8, lineHeight: 1.5 }}>
            Tu historial de conversaciones aparece acá una vez que arranques.
          </div>
        )}
        {sessions.map(s => (
          <div key={s.id} className={`assistant-conv ${s.id === currentSessionId ? "active" : ""}`}
            onClick={() => onLoadSession && onLoadSession(s.id)}
            style={{ position: "relative", cursor: "pointer" }}>
            <div className="assistant-conv-name">{s.name || "Conversación"}</div>
            <div className="assistant-conv-prev">{s.preview || "Sin mensajes"}</div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 2 }}>
              <div className="assistant-conv-time">{fmtTime(s.updated_at)}</div>
              <button
                onClick={e => handleDelete(e, s.id)}
                style={{ background: "none", border: "none", cursor: "pointer", padding: "2px 4px", fontSize: 10, color: deleteConfirm === s.id ? "var(--danger)" : "var(--fg-subtle)", borderRadius: 3 }}
                title={deleteConfirm === s.id ? "Confirmar borrar" : "Borrar"}>
                {deleteConfirm === s.id ? "¿Borrar?" : Is.x(10)}
              </button>
            </div>
          </div>
        ))}
      </aside>

      <div className="chat-full">
        <ChatPanel
          messages={messages}
          onSend={onSend}
          onConfirm={onConfirm}
          onOpenProject={onOpenProject}
        />
      </div>
    </div>
  );
}

// =====================================================================
// CONFIGURACIÓN
// =====================================================================
function ConfigSection({ theme, setTheme, tweaks, setTweak, onLogout, projects = [] }) {
  const tweak = tweaks || {};
  const density = tweak.density || "cozy";
  const accentHue = tweak.accentHue || 280;
  const kanbanView = tweak.kanbanView || "columns";
  const [tab, setTab] = useS("perfil");
  const [notif, setNotif] = useS({ alerts: true, daily: true, blockers: true, mail: false });

  return (
    <section className="section">
      <div className="section-head">
        <div>
          <div className="section-eyebrow">Configuración</div>
          <h1 className="section-title">Ajustes</h1>
          <p className="section-subtitle">Perfil, apariencia, notificaciones e integraciones</p>
        </div>
      </div>

      <div className="config-grid">
        <nav className="config-nav">
          {[
            { id: "perfil", label: "Perfil", icon: Is.user(14) },
            { id: "apariencia", label: "Apariencia", icon: Is.spark(14) },
            { id: "notificaciones", label: "Notificaciones", icon: Is.alert(14) },
            { id: "integraciones", label: "Integraciones", icon: Is.link(14) },
            { id: "asistente", label: "Asistente IA", icon: Is.sparkles(14) },
            { id: "datos", label: "Datos & exportación", icon: Is.folder(14) },
          ].map(t => (
            <button key={t.id} className={tab === t.id ? "active" : ""} onClick={() => setTab(t.id)}>
              {t.icon} {t.label}
            </button>
          ))}
        </nav>

        <div>
          {tab === "perfil" && (
            <>
              <div className="config-card">
                <h3>Perfil</h3>
                <p className="config-desc">Tu información visible en la app y en la auditoría del chat.</p>
                <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
                  <div className="user-avatar" style={{ width: 56, height: 56, fontSize: 20, borderRadius: 14 }}>AA</div>
                  <div style={{ flex: 1 }}>
                    <div className="field" style={{ marginBottom: 8 }}>
                      <label className="field-label">Nombre</label>
                      <input className="field-input" defaultValue="Alexis Arrechea" />
                    </div>
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 14 }}>
                  <div className="field">
                    <label className="field-label">Email</label>
                    <input className="field-input" defaultValue="alexis@estudioarrechea.com.ar" />
                  </div>
                  <div className="field">
                    <label className="field-label">Cliente principal</label>
                    <input className="field-input" defaultValue="Estudio Jurídico Arrechea" />
                  </div>
                </div>
                <div style={{ marginTop: 14, display: "flex", gap: 8 }}>
                  <button className="btn btn-primary" onClick={() => alert("Próximamente: actualización de perfil desde la API.")}>Guardar cambios</button>
                  <button className="btn btn-ghost" onClick={() => {}}>Cancelar</button>
                </div>
              </div>

              <div className="config-card">
                <h3>Seguridad</h3>
                <p className="config-desc">Tu sesión expira en 23 horas.</p>
                <div className="config-row">
                  <div>
                    <div className="row-label">Cambiar contraseña</div>
                    <div className="row-desc">Última actualización hace 32 días</div>
                  </div>
                  <button className="btn btn-ghost" style={{ height: 32 }}>Cambiar</button>
                </div>
                <div className="config-row">
                  <div>
                    <div className="row-label">Cerrar todas las sesiones</div>
                    <div className="row-desc">Te deslogueás de todos los dispositivos</div>
                  </div>
                  <button className="btn btn-ghost" style={{ height: 32, color: "var(--danger)" }} onClick={onLogout}>
                    Cerrar sesión
                  </button>
                </div>
              </div>
            </>
          )}

          {tab === "apariencia" && (
            <>
              <div className="config-card">
                <h3>Tema</h3>
                <p className="config-desc">Cambiá entre claro y oscuro según tu ambiente.</p>
                <div className="config-row">
                  <div>
                    <div className="row-label">Modo oscuro</div>
                    <div className="row-desc">Ideal para sesiones largas o iluminación baja</div>
                  </div>
                  <div className={`switch ${theme === "dark" ? "on" : ""}`}
                    onClick={() => setTheme(theme === "dark" ? "light" : "dark")} />
                </div>
              </div>

              <div className="config-card">
                <h3>Color de acento</h3>
                <p className="config-desc">El acento se usa en CTAs, gráficos y estados activos.</p>
                <div className="swatch-grid">
                  {[
                    { h: 280, name: "Violeta" },
                    { h: 250, name: "Índigo" },
                    { h: 210, name: "Cobalto" },
                    { h: 160, name: "Verde" },
                    { h: 30, name: "Naranja" },
                    { h: 5, name: "Coral" },
                  ].map(({ h, name }) => (
                    <button key={h} title={name}
                      className={`swatch-btn ${accentHue === h ? "active" : ""}`}
                      onClick={() => setTweak("accentHue", h)}
                      style={{ background: `oklch(0.55 0.20 ${h})` }} />
                  ))}
                </div>
              </div>

              <div className="config-card">
                <h3>Densidad</h3>
                <p className="config-desc">Cuánto aire entre elementos.</p>
                <div className="filter-bar">
                  {["compact", "cozy", "comfy"].map(d => (
                    <button key={d}
                      className={`filter-chip ${density === d ? "active" : ""}`}
                      onClick={() => setTweak("density", d)}>
                      {d === "compact" ? "Compacto" : d === "cozy" ? "Cómodo" : "Amplio"}
                    </button>
                  ))}
                </div>
              </div>

              <div className="config-card">
                <h3>Vista por defecto de proyectos</h3>
                <p className="config-desc">Cuál vista mostrar al entrar a la sección Proyectos.</p>
                <div className="filter-bar">
                  {["columns", "list", "timeline"].map(v => (
                    <button key={v}
                      className={`filter-chip ${kanbanView === v ? "active" : ""}`}
                      onClick={() => setTweak("kanbanView", v)}>
                      {v === "columns" ? "Columnas" : v === "list" ? "Lista" : "Timeline"}
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}

          {tab === "notificaciones" && (
            <div className="config-card">
              <h3>Notificaciones</h3>
              <p className="config-desc">Qué te avisamos y cómo.</p>
              {[
                { k: "alerts", label: "Proyectos en riesgo", desc: "Alertas cuando un proyecto supera el estimado o lleva +3 días sin movimiento" },
                { k: "blockers", label: "Bloqueadores nuevos", desc: "Cuando aparece un impedimento en cualquier proyecto" },
                { k: "daily", label: "Resumen diario", desc: "A las 9:00 AM, resumen del día anterior" },
                { k: "mail", label: "Por email", desc: "Repetir las notificaciones críticas por mail" },
              ].map(n => (
                <div key={n.k} className="config-row">
                  <div>
                    <div className="row-label">{n.label}</div>
                    <div className="row-desc">{n.desc}</div>
                  </div>
                  <div className={`switch ${notif[n.k] ? "on" : ""}`}
                    onClick={() => setNotif(s => ({ ...s, [n.k]: !s[n.k] }))} />
                </div>
              ))}
            </div>
          )}

          {tab === "integraciones" && <IntegracionesTab />}

          {tab === "asistente" && (
            <>
              <div className="config-card">
                <h3>Personalidad del agente</h3>
                <p className="config-desc">Cómo te habla tu asistente IA.</p>
                <div className="filter-bar">
                  {["Cálido coach", "Directo técnico", "Conciso analítico"].map(t => (
                    <button key={t}
                      className={`filter-chip ${tweak.agentTone === t ? "active" : ""}`}
                      onClick={() => setTweak("agentTone", t)}>
                      {t}
                    </button>
                  ))}
                </div>
              </div>
              <div className="config-card">
                <h3>Comportamiento</h3>
                <div className="config-row">
                  <div>
                    <div className="row-label">Pedir confirmación antes de cambios</div>
                    <div className="row-desc">Recomendado · evita modificaciones por error</div>
                  </div>
                  <div className="switch on" />
                </div>
                <div className="config-row">
                  <div>
                    <div className="row-label">Análisis proactivo</div>
                    <div className="row-desc">El agente inicia conversaciones cuando detecta riesgos</div>
                  </div>
                  <div className="switch on" />
                </div>
                <div className="config-row">
                  <div>
                    <div className="row-label">Avatares en chat</div>
                    <div className="row-desc">Mostrar iniciales junto a cada mensaje</div>
                  </div>
                  <div className={`switch ${tweak.showAvatars ? "on" : ""}`}
                    onClick={() => setTweak("showAvatars", !tweak.showAvatars)} />
                </div>
              </div>
            </>
          )}

          {tab === "datos" && (
            <>
              <div className="config-card">
                <h3>Exportar datos</h3>
                <p className="config-desc">Descargá tus proyectos, tareas, horas y conversaciones en formato JSON o CSV.</p>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button className="btn btn-ghost" onClick={() => {
                    const data = JSON.stringify(projects.map(p => ({ id: p.id, name: p.name, state: p.state, priority: p.priority, actualHours: p.actualHours, estimatedHours: p.estimatedHours, tasks: p.tasks, blocked: p.blocked })), null, 2);
                    const blob = new Blob([data], { type: "application/json" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a"); a.href = url; a.download = "maestro-proyectos.json"; a.click();
                    URL.revokeObjectURL(url);
                  }}>Exportar JSON</button>
                  <button className="btn btn-ghost" onClick={() => Ds.exportProjectsCSV(projects)}>Proyectos CSV</button>
                  <button className="btn btn-ghost" onClick={() => Ds.exportTasksCSV(projects)}>Tareas CSV</button>
                </div>
              </div>
              <div className="config-card">
                <h3 style={{ color: "var(--danger)" }}>Zona peligrosa</h3>
                <p className="config-desc">Acciones que no se pueden deshacer.</p>
                <div className="config-row">
                  <div>
                    <div className="row-label">Borrar historial de chat</div>
                    <div className="row-desc">Resetea la memoria del agente</div>
                  </div>
                  <button className="btn btn-ghost" style={{ height: 32, color: "var(--danger)" }}>Borrar</button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

// =====================================================================
// GOOGLE OAUTH FIELDS
// =====================================================================
function GoogleOAuthFields({ cfg, form, setF, saving, onSave, onConnect, onDisconnect }) {
  const oauthConnected = cfg?.google?.oauth_connected;
  const hasCredentials = form.google_oauth_client_id && form.google_oauth_client_secret;
  const inputStyle = { width: "100%", boxSizing: "border-box", padding: "8px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 13 };
  const labelStyle = { fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 4, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.04em" };
  const hintStyle = { fontSize: 11, color: "var(--text-muted)", marginTop: 4, lineHeight: 1.5 };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

      {/* Estado OAuth */}
      {oauthConnected ? (
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "var(--r-md)" }}>
          <span style={{ fontSize: 22 }}>✓</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, color: "#16a34a", fontSize: 14 }}>Conectado con tu cuenta de Google</div>
            <div style={{ fontSize: 12, color: "#4ade80" }}>Drive y Calendar personal activos</div>
          </div>
          <button onClick={onDisconnect} style={{ padding: "6px 12px", borderRadius: "var(--r-sm)", border: "1px solid #fca5a5", background: "white", color: "#dc2626", fontSize: 12, cursor: "pointer", fontWeight: 500 }}>
            Desconectar
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ padding: "12px 14px", background: "var(--bg-subtle)", borderRadius: "var(--r-md)", fontSize: 12, lineHeight: 1.6, color: "var(--text-muted)", borderLeft: "3px solid var(--accent)" }}>
            <strong style={{ color: "var(--text-primary)" }}>Cómo conectar tu cuenta personal:</strong>
            <ol style={{ margin: "6px 0 0 0", paddingLeft: 18 }}>
              <li>Andá a <strong>console.cloud.google.com</strong> → APIs → Credenciales</li>
              <li>Creá una credencial <strong>OAuth 2.0 (Web Application)</strong></li>
              <li>En "URI de redireccionamiento autorizados" agregá: <code style={{ background: "var(--bg-base)", padding: "1px 4px", borderRadius: 3, fontSize: 11 }}>http://2.24.108.79:8000/settings/google/callback</code></li>
              <li>Copiá el <strong>Client ID</strong> y <strong>Client Secret</strong> abajo</li>
              <li>Hacé click en <strong>"Guardar y conectar con Google"</strong></li>
            </ol>
          </div>

          <div>
            <label style={labelStyle}>Client ID</label>
            <input style={inputStyle} placeholder="xxxxxxxxxxxx.apps.googleusercontent.com"
              value={form.google_oauth_client_id || ""}
              onChange={e => setF("google_oauth_client_id", e.target.value)} />
          </div>
          <div>
            <label style={labelStyle}>Client Secret</label>
            <input style={{ ...inputStyle, fontFamily: "monospace" }} type="password" placeholder="GOCSPX-..."
              value={form.google_oauth_client_secret || ""}
              onChange={e => setF("google_oauth_client_secret", e.target.value)} />
          </div>

          <button
            onClick={onConnect}
            disabled={!hasCredentials || saving}
            style={{
              display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
              padding: "10px 20px", borderRadius: "var(--r-md)", border: "none",
              background: hasCredentials ? "linear-gradient(135deg,#4285F4,#34A853)" : "var(--bg-subtle)",
              color: hasCredentials ? "white" : "var(--text-muted)",
              fontWeight: 600, fontSize: 14, cursor: hasCredentials ? "pointer" : "default",
              transition: "opacity .2s",
            }}>
            <span style={{ fontSize: 18 }}>G</span>
            {saving ? "Guardando..." : "Guardar y conectar con Google"}
          </button>
          <p style={hintStyle}>Se abrirá una ventana de Google para que autorizces el acceso a tu Drive y Calendar personal.</p>
        </div>
      )}

      {/* Opciones adicionales — siempre visibles */}
      <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <div>
          <label style={labelStyle}>Drive — ID carpeta raíz</label>
          <input style={inputStyle} placeholder="1BxiM... (opcional)"
            value={form.google_drive_folder_id || ""}
            onChange={e => setF("google_drive_folder_id", e.target.value)} />
          <p style={hintStyle}>URL de la carpeta → último segmento. Dejalo vacío para usar la raíz.</p>
        </div>
        <div>
          <label style={labelStyle}>Calendar ID</label>
          <input style={inputStyle} placeholder="primary"
            value={form.google_calendar_id || ""}
            onChange={e => setF("google_calendar_id", e.target.value)} />
          <p style={hintStyle}>"primary" = tu calendario principal.</p>
        </div>
      </div>
      <button
        onClick={() => onSave(["google_drive_folder_id", "google_calendar_id"])}
        disabled={saving}
        style={{ alignSelf: "flex-start", padding: "7px 16px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-subtle)", color: "var(--text-primary)", fontSize: 13, cursor: "pointer", fontWeight: 500 }}>
        {saving ? "Guardando..." : "Guardar configuración de carpeta/calendario"}
      </button>
    </div>
  );
}


// =====================================================================
// INTEGRACIONES TAB — lee y escribe .env via API
// =====================================================================
function IntegracionesTab() {
  const [cfg, setCfg] = useS(null);
  const [open, setOpen] = useS(null);  // qué card está expandida
  const [form, setForm] = useS({});
  const [saving, setSaving] = useS(false);
  const [testing, setTesting] = useS(null);
  const [testResult, setTestResult] = useS({});
  const [toast, setToast] = useS(null);
  const [googleSAEmail, setGoogleSAEmail] = useS(null);

  useE(() => {
    Ds.API.getIntegrations()
      .then(data => { setCfg(data); setForm(buildFormDefaults(data)); })
      .catch(err => {
        setToast({ text: "No se pudo cargar la configuración: " + (err?.message || "error de red"), kind: "error" });
        // Fallback para que no quede colgado en loading
        const empty = { env_file_exists: false, claude: {}, supabase: {}, google: {}, github: {}, whatsapp: {} };
        setCfg(empty);
        setForm(buildFormDefaults(empty));
      });
    Ds.API.getGoogleServiceAccountEmail()
      .then(data => { if (data?.email) setGoogleSAEmail(data.email); })
      .catch(() => {});
  }, []);

  function buildFormDefaults(data) {
    if (!data) return {};
    return {
      anthropic_api_key: data.claude?.api_key || "",
      supabase_url: data.supabase?.url || "",
      supabase_key: data.supabase?.key || "",
      google_oauth_client_id: data.google?.oauth_client_id || "",
      google_oauth_client_secret: data.google?.oauth_client_secret || "",
      google_credentials_path: data.google?.credentials_path || "",
      google_drive_folder_id: data.google?.drive_folder_id || "",
      google_calendar_id: data.google?.calendar_id || "primary",
      github_token: data.github?.token || "",
      whatsapp_provider: data.whatsapp?.provider || "twilio",
      twilio_account_sid: data.whatsapp?.twilio_account_sid || "",
      twilio_auth_token: data.whatsapp?.twilio_auth_token || "",
      twilio_from: data.whatsapp?.twilio_from || "",
      meta_token: data.whatsapp?.meta_token || "",
      meta_phone_id: data.whatsapp?.meta_phone_id || "",
      meta_verify_token: data.whatsapp?.verify_token || "",
      claude_model: data.claude?.model || "",
    };
  }

  function setF(key, value) { setForm(f => ({ ...f, [key]: value })); }

  async function save(serviceKey, fields) {
    setSaving(true);
    try {
      const payload = {};
      fields.forEach(k => { payload[k] = form[k]; });
      const res = await Ds.API.saveIntegrations(payload);
      if (res.updated?.length) {
        setToast({ text: `✓ Guardado en .env — reiniciá el servidor para aplicar.`, kind: "success" });
        // Actualización local optimista: marcar la integración como configurada
        setCfg(prev => {
          if (!prev) return prev;
          const next = { ...prev };
          const serviceMap = {
            claude: "claude", supabase: "supabase", google: "google",
            github: "github", whatsapp: "whatsapp",
          };
          const svc = serviceMap[serviceKey];
          if (svc && next[svc]) {
            next[svc] = { ...next[svc], enabled: true, _pending_restart: true };
          }
          return next;
        });
        setOpen(null);
      } else {
        setToast({ text: res.message || "Sin cambios que guardar.", kind: "info" });
      }
    } catch (e) {
      setToast({ text: "Error al guardar: " + e.message, kind: "error" });
    } finally {
      setSaving(false);
    }
  }

  async function testConn(service) {
    setTesting(service);
    try {
      const res = await Ds.API.testService(service);
      setTestResult(r => ({ ...r, [service]: res }));
    } catch (e) {
      setTestResult(r => ({ ...r, [service]: { ok: false, message: e.message } }));
    } finally {
      setTesting(null);
    }
  }

  useE(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(id);
  }, [toast]);

  if (!cfg) return (
    <div className="config-card" style={{ textAlign: "center", padding: 40, color: "var(--fg-muted)" }}>
      <div className="typing-dots" style={{ justifyContent: "center", marginBottom: 10 }}>
        <span /><span /><span />
      </div>
      Cargando configuración…
    </div>
  );

  const integrations = [
    {
      id: "claude",
      logo: "C",
      color: "linear-gradient(135deg, #D97757, #b9522a)",
      name: "Claude API",
      desc: "Motor de IA que alimenta el asistente conversacional.",
      enabled: cfg.claude?.enabled,
      _pending_restart: cfg.claude?._pending_restart,
      fields: (
        <>
          <div className="field">
            <label className="field-label">API Key (ANTHROPIC_API_KEY)</label>
            <input className="field-input" type="password" placeholder="sk-ant-api03-..."
              value={form.anthropic_api_key} onChange={e => setF("anthropic_api_key", e.target.value)} />
            <p className="row-desc" style={{ marginTop: 4 }}>
              Obtener en <code>console.anthropic.com</code> → API Keys. El valor actual está enmascarado si ya está configurado.
            </p>
          </div>
          <div className="field" style={{ marginTop: 10 }}>
            <label className="field-label">Modelo</label>
            <select className="field-input" value={form.claude_model} onChange={e => setF("claude_model", e.target.value)}>
              <option value="claude-haiku-4-5-20251001">Claude Haiku 4.5 (rápido y económico)</option>
              <option value="claude-sonnet-4-6">Claude Sonnet 4.6 (equilibrado)</option>
              <option value="claude-opus-4-7">Claude Opus 4.7 (más potente)</option>
            </select>
          </div>
        </>
      ),
      saveFields: ["anthropic_api_key", "claude_model"],
    },
    {
      id: "supabase",
      logo: "S",
      color: "linear-gradient(135deg, #3ECF8E, #1f7c5b)",
      name: "Supabase",
      desc: "Base de datos PostgreSQL en la nube. Reemplaza SQLite para producción.",
      enabled: cfg.supabase?.enabled,
      _pending_restart: cfg.supabase?._pending_restart,
      fields: (
        <>
          <div className="field">
            <label className="field-label">Project URL</label>
            <input className="field-input" placeholder="https://[ref].supabase.co"
              value={form.supabase_url} onChange={e => setF("supabase_url", e.target.value)} />
          </div>
          <div className="field" style={{ marginTop: 10 }}>
            <label className="field-label">Anon / Service Key</label>
            <input className="field-input" type="password" placeholder="eyJ..."
              value={form.supabase_key} onChange={e => setF("supabase_key", e.target.value)} />
          </div>
          <p className="row-desc" style={{ marginTop: 8 }}>
            Para usar Supabase como BD, también cambiá DATABASE_URL a la connection string de PostgreSQL.
          </p>
        </>
      ),
      saveFields: ["supabase_url", "supabase_key"],
    },
    {
      id: "google",
      logo: "G",
      color: "linear-gradient(135deg, #4285F4, #34A853)",
      name: "Google Drive & Calendar",
      desc: "Carpetas por proyecto en Drive y eventos de deadline en Calendar.",
      enabled: cfg.google?.enabled,
      _pending_restart: cfg.google?._pending_restart,
      fields: (
        <GoogleOAuthFields
          cfg={cfg}
          form={form}
          setF={setF}
          saving={saving}
          onSave={(fields) => save("google", fields)}
          onConnect={async () => {
            // Guardar client_id y secret primero
            await save("google", ["google_oauth_client_id", "google_oauth_client_secret"]);
            try {
              const res = await Ds.API.apiFetch("/settings/google/auth-url");
              const popup = window.open(res.url, "google-oauth", "width=560,height=660,left=200,top=100");
              const handler = (e) => {
                if (e.data?.type === "maestro:google-connected") {
                  window.removeEventListener("message", handler);
                  // Recargar cfg desde backend
                  Ds.API.getIntegrations()
                    .then(data => { setCfg(data); setForm(buildFormDefaults(data)); });
                }
              };
              window.addEventListener("message", handler);
            } catch(e) {
              setToast({ text: "Error: " + e.message, kind: "error" });
            }
          }}
          onDisconnect={async () => {
            try {
              await Ds.API.apiFetch("/settings/google/disconnect", { method: "POST" });
              Ds.API.getIntegrations().then(data => { setCfg(data); setForm(buildFormDefaults(data)); });
              setToast({ text: "Cuenta de Google desconectada.", kind: "success" });
            } catch(e) {
              setToast({ text: "Error: " + e.message, kind: "error" });
            }
          }}
        />
      ),
      saveFields: [],
    },
    {
      id: "github",
      logo: "◆",
      color: "linear-gradient(135deg, #24292e, #444)",
      name: "GitHub",
      desc: "Vinculá proyectos a repositorios y consultá commits y PRs desde el chat.",
      enabled: cfg.github?.enabled,
      _pending_restart: cfg.github?._pending_restart,
      fields: (
        <div className="field">
          <label className="field-label">Personal Access Token</label>
          <input className="field-input" type="password" placeholder="ghp_..."
            value={form.github_token} onChange={e => setF("github_token", e.target.value)} />
          <p className="row-desc" style={{ marginTop: 4 }}>
            Generalo en github.com/settings/tokens · Scopes: <code>repo</code> o <code>public_repo</code>
          </p>
        </div>
      ),
      saveFields: ["github_token"],
    },
    {
      id: "whatsapp",
      logo: "W",
      color: "linear-gradient(135deg, #25D366, #128C7E)",
      name: "WhatsApp",
      desc: "Conectá el asistente a un número de WhatsApp para chatear desde el teléfono.",
      enabled: cfg.whatsapp?.enabled,
      _pending_restart: cfg.whatsapp?._pending_restart,
      fields: (
        <>
          <div className="field" style={{ marginBottom: 12 }}>
            <label className="field-label">Proveedor</label>
            <div className="filter-bar">
              {["twilio", "meta"].map(p => (
                <button key={p} type="button"
                  className={`filter-chip ${form.whatsapp_provider === p ? "active" : ""}`}
                  onClick={() => setF("whatsapp_provider", p)}>
                  {p === "twilio" ? "Twilio (recomendado)" : "Meta Cloud API"}
                </button>
              ))}
            </div>
          </div>

          {form.whatsapp_provider === "twilio" ? (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div className="field">
                  <label className="field-label">Account SID</label>
                  <input className="field-input" placeholder="ACxxxxxxxx"
                    value={form.twilio_account_sid} onChange={e => setF("twilio_account_sid", e.target.value)} />
                </div>
                <div className="field">
                  <label className="field-label">Auth Token</label>
                  <input className="field-input" type="password" placeholder="••••••••"
                    value={form.twilio_auth_token} onChange={e => setF("twilio_auth_token", e.target.value)} />
                </div>
              </div>
              <div className="field" style={{ marginTop: 10 }}>
                <label className="field-label">Número WhatsApp de MAESTRO</label>
                <input className="field-input" placeholder="whatsapp:+14155238886"
                  value={form.twilio_from} onChange={e => setF("twilio_from", e.target.value)} />
              </div>
              <div style={{ marginTop: 12, padding: "10px 12px", background: "var(--bg-subtle)", borderRadius: "var(--r-md)", fontSize: 12, color: "var(--fg-muted)", lineHeight: 1.6 }}>
                <strong>Webhook a configurar en Twilio Console:</strong><br />
                <code style={{ color: "var(--accent)" }}>POST https://tu-dominio.com/whatsapp/webhook</code>
              </div>
            </>
          ) : (
            <>
              <div className="field">
                <label className="field-label">Access Token</label>
                <input className="field-input" type="password" placeholder="EAAxxxxxxx"
                  value={form.meta_token} onChange={e => setF("meta_token", e.target.value)} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 10 }}>
                <div className="field">
                  <label className="field-label">Phone ID</label>
                  <input className="field-input" placeholder="1234567890"
                    value={form.meta_phone_id} onChange={e => setF("meta_phone_id", e.target.value)} />
                </div>
                <div className="field">
                  <label className="field-label">Verify Token</label>
                  <input className="field-input" placeholder="maestro-webhook-token"
                    value={form.meta_verify_token} onChange={e => setF("meta_verify_token", e.target.value)} />
                </div>
              </div>
            </>
          )}
        </>
      ),
      saveFields: ["whatsapp_provider", "twilio_account_sid", "twilio_auth_token", "twilio_from",
                   "meta_token", "meta_phone_id", "meta_verify_token"],
    },
  ];

  return (
    <div>
      {toast && (
        <div className={`toast`} data-kind={toast.kind} style={{
          marginBottom: 16, padding: "10px 14px", borderRadius: "var(--r-md)",
          background: toast.kind === "error" ? "var(--danger-soft)" : "var(--success-soft)",
          border: `1px solid var(--${toast.kind === "error" ? "danger" : "success"})`,
          fontSize: 13, fontWeight: 500,
        }}>
          {toast.text}
        </div>
      )}

      {!cfg.env_file_exists && (
        <div className="config-card" style={{ borderLeft: "3px solid var(--warning)", marginBottom: 12 }}>
          <strong style={{ color: "var(--warning)" }}>Archivo .env no encontrado</strong>
          <p className="config-desc" style={{ marginTop: 4 }}>
            Al guardar cualquier integración se creará automáticamente desde <code>.env.example</code>.
          </p>
        </div>
      )}

      {integrations.map(int => (
        <div key={int.id} className="config-card" style={{ marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, cursor: "pointer" }}
            onClick={() => setOpen(open === int.id ? null : int.id)}>
            <div className="integration-logo" style={{ background: int.color, flexShrink: 0 }}>
              {int.logo}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span className="integration-name">{int.name}</span>
                <span style={{
                  width: 7, height: 7, borderRadius: "50%",
                  background: int.enabled ? (int._pending_restart ? "var(--warning)" : "var(--success)") : "var(--fg-subtle)",
                  display: "inline-block",
                }} />
                {int._pending_restart && (
                  <span style={{ fontSize: 10, color: "var(--warning)", fontWeight: 600 }}>reinicio pendiente</span>
                )}
                {testResult[int.id] && (
                  <span style={{ fontSize: 11, color: testResult[int.id].ok ? "var(--success)" : "var(--danger)" }}>
                    {testResult[int.id].ok ? "✓" : "✗"} {testResult[int.id].message}
                  </span>
                )}
              </div>
              <div className={`integration-status ${int.enabled ? "ok" : ""}`}>
                {int.enabled
                  ? (int._pending_restart ? "Guardado — reiniciá el servidor" : "Conectado")
                  : "Sin configurar"} · {int.desc}
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
              <button className="btn btn-ghost" style={{ height: 30, fontSize: 11 }}
                onClick={e => { e.stopPropagation(); testConn(int.id); }}
                disabled={testing === int.id}>
                {testing === int.id ? "…" : "Probar"}
              </button>
              <button className="btn btn-ghost" style={{ height: 30, fontSize: 11 }}
                onClick={e => { e.stopPropagation(); setOpen(open === int.id ? null : int.id); }}>
                {open === int.id ? "Cerrar" : "Configurar"}
              </button>
            </div>
          </div>

          {open === int.id && (
            <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
              {int.fields}
              <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
                <button className="btn btn-primary" style={{ height: 34, fontSize: 13 }}
                  onClick={() => save(int.id, int.saveFields)}
                  disabled={saving}>
                  {saving ? "Guardando…" : "Guardar en .env"}
                </button>
                <button className="btn btn-ghost" style={{ height: 34, fontSize: 13 }}
                  onClick={() => setOpen(null)}>
                  Cancelar
                </button>
              </div>
            </div>
          )}
        </div>
      ))}

      <div style={{ padding: "12px 16px", background: "var(--bg-subtle)", borderRadius: "var(--r-md)", fontSize: 12, color: "var(--fg-muted)", lineHeight: 1.7 }}>
        <strong>Nota:</strong> Los cambios se guardan en <code>backend/.env</code> y requieren reiniciar el servidor para aplicarse.<br />
        Los secretos (tokens, passwords) se muestran enmascarados y nunca salen del servidor.
      </div>
    </div>
  );
}

// =====================================================================
// REUNIONES
// =====================================================================
function NewMeetingModal({ projects, onClose, onSave }) {
  const [projectId, setProjectId] = useS(projects[0]?.id || "");
  const [desc, setDesc] = useS("");
  const [meetingWith, setMeetingWith] = useS("");
  const [meetingDate, setMeetingDate] = useS("");
  const [prepFile, setPrepFile] = useS(null);
  const [saving, setSaving] = useS(false);

  const inputStyle = { width: "100%", boxSizing: "border-box", padding: "8px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 14 };
  const labelStyle = { fontSize: 12, color: "var(--fg-muted)", display: "block", marginBottom: 4 };

  const submit = async (e) => {
    e.preventDefault();
    if (!desc.trim() || !projectId) return;
    setSaving(true);
    try {
      await onSave({ projectId, taskName: desc.trim(), taskType: "meeting", meetingWith: meetingWith.trim() || null, fechaVencimiento: meetingDate || null, prepFile: prepFile || null });
      onClose();
    } finally { setSaving(false); }
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: "var(--r-lg)", padding: 28, width: 460, maxWidth: "90vw" }}>
        <h2 style={{ margin: "0 0 4px", fontSize: 16, fontWeight: 600 }}>Nueva reunión</h2>
        <p style={{ margin: "0 0 20px", fontSize: 13, color: "var(--fg-muted)" }}>Agregá la reunión a un proyecto y dejate un archivo de preparación</p>
        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label style={labelStyle}>Proyecto *</label>
            <select value={projectId} onChange={e => setProjectId(e.target.value)} required style={inputStyle}>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>De qué se trata *</label>
            <input autoFocus value={desc} onChange={e => setDesc(e.target.value)} placeholder="Ej: Revisión de avance del proyecto ARCA" required style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Con quién</label>
            <input value={meetingWith} onChange={e => setMeetingWith(e.target.value)} placeholder="Ej: Juan Pérez, cliente ACME" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Fecha de la reunión</label>
            <input type="date" value={meetingDate} onChange={e => setMeetingDate(e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Archivo de preparación (opcional, máx. 10 MB)</label>
            <input type="file" accept=".pdf,.doc,.docx,.txt,.md,.pptx,.xlsx,.png,.jpg" style={{ fontSize: 13, color: "var(--text-primary)" }}
              onChange={e => setPrepFile(e.target.files[0] || null)} />
          </div>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 8 }}>
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={saving || !desc.trim() || !projectId}>
              {saving ? "Guardando…" : "Crear reunión"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function MeetingsSection({ projects, onOpenProject, onAddTask }) {
  const [filter, setFilter] = useS("proximas");
  const [projFilter, setProjFilter] = useS("all");
  const [showModal, setShowModal] = useS(false);

  const todayISO = new Date().toISOString().slice(0, 10);

  const allMeetings = useM(() => {
    const a = [];
    projects.forEach(p => {
      (p.tasks || []).forEach(t => {
        if (t.taskType === "meeting") a.push({ ...t, project: p });
      });
    });
    return a.sort((a, b) => {
      if (!a.fechaVencimiento && !b.fechaVencimiento) return 0;
      if (!a.fechaVencimiento) return 1;
      if (!b.fechaVencimiento) return -1;
      return a.fechaVencimiento.localeCompare(b.fechaVencimiento);
    });
  }, [projects]);

  const filtered = useM(() => {
    let r = allMeetings;
    if (filter === "proximas") r = r.filter(t => !t.done && (!t.fechaVencimiento || t.fechaVencimiento >= todayISO));
    if (filter === "pasadas") r = r.filter(t => t.done || (t.fechaVencimiento && t.fechaVencimiento < todayISO));
    if (projFilter !== "all") r = r.filter(t => t.project.id === projFilter);
    return r;
  }, [allMeetings, filter, projFilter, todayISO]);

  return (
    <section className="section">
      {showModal && projects.length > 0 && (
        <NewMeetingModal projects={projects} onClose={() => setShowModal(false)} onSave={onAddTask} />
      )}
      <div className="section-head">
        <div>
          <div className="section-eyebrow">Reuniones</div>
          <h1 className="section-title">Todas las reuniones</h1>
          <p className="section-subtitle">
            {allMeetings.length === 0
              ? "Agendá reuniones asociadas a tus proyectos"
              : `${allMeetings.filter(t => !t.done && (!t.fechaVencimiento || t.fechaVencimiento >= todayISO)).length} próximas · ${allMeetings.filter(t => t.done || (t.fechaVencimiento && t.fechaVencimiento < todayISO)).length} pasadas`}
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => projects.length > 0 ? setShowModal(true) : null}>
          {Is.meeting(14)} Nueva reunión
        </button>
      </div>

      <div className="filter-bar">
        {[["proximas","Próximas"], ["pasadas","Pasadas"], ["all","Todas"]].map(([v,l]) => (
          <button key={v} className={`filter-chip ${filter === v ? "active" : ""}`} onClick={() => setFilter(v)}>{l}</button>
        ))}
        <div style={{ width: 1, height: 22, background: "var(--border)", margin: "0 6px" }} />
        <button className={`filter-chip ${projFilter === "all" ? "active" : ""}`} onClick={() => setProjFilter("all")}>Todos los proyectos</button>
        {projects.slice(0, 5).map(p => (
          <button key={p.id} className={`filter-chip ${projFilter === p.id ? "active" : ""}`} onClick={() => setProjFilter(p.id)}>{p.name}</button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="empty-hero">
          <div className="empty-hero-mark">{Is.meeting(28)}</div>
          <h2>Sin reuniones {filter === "proximas" ? "próximas" : filter === "pasadas" ? "pasadas" : ""}</h2>
          <p>Usá el botón "Nueva reunión" para agendar una reunión dentro de un proyecto.</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {filtered.map(t => {
            const isPast = t.fechaVencimiento && t.fechaVencimiento < todayISO;
            const isToday = t.fechaVencimiento === todayISO;
            return (
              <div key={t.id} style={{
                background: "var(--bg-surface)", border: "1px solid var(--border)",
                borderLeft: `3px solid ${t.done ? "var(--fg-subtle)" : isToday ? "var(--warning)" : isPast ? "var(--danger)" : "var(--accent)"}`,
                borderRadius: "var(--r-md)", padding: "14px 18px",
                opacity: t.done ? 0.7 : 1,
              }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                  <div style={{ color: "var(--accent)", marginTop: 1, flexShrink: 0 }}>{Is.meeting(16)}</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 6, textDecoration: t.done ? "line-through" : "none", color: t.done ? "var(--fg-muted)" : "var(--text-primary)" }}>
                      {t.name}
                    </div>
                    <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: 12, color: "var(--fg-muted)" }}>
                      {t.meetingWith && (
                        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                          {Is.users(11)} {t.meetingWith}
                        </span>
                      )}
                      {t.fechaVencimiento && (
                        <span style={{ fontWeight: isToday ? 700 : 400, color: isToday ? "var(--warning)" : isPast && !t.done ? "var(--danger)" : "inherit" }}>
                          {isToday ? "HOY" : t.fechaVencimiento}
                        </span>
                      )}
                      <span style={{ color: "var(--accent)", cursor: "pointer" }} onClick={() => onOpenProject(t.project.id)}>
                        {t.project.name} →
                      </span>
                      {t.meetingPrepUrl && (
                        <a href={t.meetingPrepUrl} target="_blank" rel="noopener noreferrer"
                          style={{ color: "var(--accent)", textDecoration: "none", display: "flex", alignItems: "center", gap: 3 }}>
                          📎 {t.meetingPrepFilename || "Archivo prep"}
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

window.MAESTRO_SECTIONS = {
  TareasSection,
  CalendarioSection,
  StatsSection,
  AsistenteSection,
  ConfigSection,
  MeetingsSection,
};
