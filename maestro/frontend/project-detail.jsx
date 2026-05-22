// =====================================================================
// MAESTRO — Carpeta de proyecto (vista de pagina completa)
// Sigue la estructura de ESPECIFICACION_CARPETA_PROYECTO.txt
// =====================================================================
const { useState: usePD, useEffect: usePDE, useMemo: usePDM } = React;
const D_pd = window.MAESTRO_DATA;
const I_pd = window.MAESTRO_ICONS;

const PD_BLOCKER_COLOR = {
  "esperando cliente": "var(--danger)",
  "sin acceso": "var(--danger)",
  "tecnico": "var(--warning)",
  "otro": "var(--fg-subtle)",
};
const PD_PRIORITY_COLOR = { alta: "var(--danger)", media: "var(--warning)", baja: "var(--success)" };
const PD_NOTE_COLOR = { learning: "var(--accent)", decision: "var(--warning)", reflection: "var(--success)", otro: "var(--fg-subtle)" };
const PD_NOTE_ICON  = { learning: "Aprendizaje", decision: "Decision", reflection: "Reflexion", otro: "Nota" };

// ── Helpers ──────────────────────────────────────────────────────────
function PDCard({ children, style }) {
  return (
    <div style={{
      background: "var(--bg-surface)", border: "1px solid var(--border)",
      borderRadius: "var(--r-lg)", padding: "20px 24px",
      ...style
    }}>
      {children}
    </div>
  );
}

function PDSectionTitle({ children }) {
  return (
    <h2 style={{ margin: "0 0 16px", fontSize: 12, fontWeight: 700, textTransform: "uppercase",
      letterSpacing: "0.08em", color: "var(--fg-subtle)" }}>
      {children}
    </h2>
  );
}

function PDMetric({ label, value, sub, color, large }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={{ fontSize: 11, color: "var(--fg-subtle)", fontWeight: 500 }}>{label}</div>
      <div style={{ fontSize: large ? 28 : 20, fontWeight: 700, color: color || "var(--text-primary)", lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: "var(--fg-muted)" }}>{sub}</div>}
    </div>
  );
}

// ── Inline forms ─────────────────────────────────────────────────────
function AddHoursForm({ project, onSave, onCancel }) {
  const [h, setH] = usePD("");
  const [desc, setDesc] = usePD("");
  const [saving, setSaving] = usePD(false);
  const s = { padding: "7px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 13 };
  const submit = async (e) => {
    e.preventDefault();
    if (!h || parseFloat(h) <= 0) return;
    setSaving(true);
    try { await onSave(parseFloat(h), desc); } finally { setSaving(false); }
  };
  return (
    <form onSubmit={submit} style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", padding: "12px 0" }}>
      <input type="number" step="0.5" min="0.5" placeholder="2.5h" value={h} onChange={e => setH(e.target.value)} style={{ ...s, width: 90 }} autoFocus />
      <input placeholder="Que hiciste?" value={desc} onChange={e => setDesc(e.target.value)} style={{ ...s, flex: 1, minWidth: 180 }} />
      <button type="submit" className="btn btn-primary" style={{ height: 34, fontSize: 13 }} disabled={saving}>{saving ? "..." : "Guardar"}</button>
      <button type="button" className="btn btn-ghost" style={{ height: 34, fontSize: 13 }} onClick={onCancel}>Cancelar</button>
    </form>
  );
}

function AddNoteForm({ onSave, onCancel }) {
  const [text, setText] = usePD("");
  const [tipo, setTipo] = usePD("otro");
  const [saving, setSaving] = usePD(false);
  const s = { padding: "7px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 13 };
  const submit = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    setSaving(true);
    try { await onSave(text.trim(), tipo); } finally { setSaving(false); }
  };
  return (
    <form onSubmit={submit} style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", padding: "12px 0" }}>
      <input placeholder="Nota, aprendizaje o decision..." value={text} onChange={e => setText(e.target.value)} style={{ ...s, flex: 1, minWidth: 200 }} autoFocus />
      <select value={tipo} onChange={e => setTipo(e.target.value)} style={{ ...s, width: 130 }}>
        <option value="otro">Nota</option>
        <option value="learning">Aprendizaje</option>
        <option value="decision">Decision</option>
        <option value="reflection">Reflexion</option>
      </select>
      <button type="submit" className="btn btn-primary" style={{ height: 34, fontSize: 13 }} disabled={saving}>{saving ? "..." : "Guardar"}</button>
      <button type="button" className="btn btn-ghost" style={{ height: 34, fontSize: 13 }} onClick={onCancel}>Cancelar</button>
    </form>
  );
}

// ── Main component ────────────────────────────────────────────────────
function fmtTimer(s) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  if (h > 0) return `${h}:${String(m).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
  return `${String(m).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
}

function ProjectDetail({ project, onClose, onToggleTask, onResolveBlocker, onAddBlocker, onChangeState, onEditProject, onAddHours, onAddNote, onDeleteProject, onUploadStructureImage, onArchiveProject, onDuplicateProject, onUpdateTaskSubtasks, onAddTask, onUploadTaskPrepFile, activeTimer, timerDisplaySeconds, onStartTimer, onPauseTimer }) {
  const [showHours, setShowHours] = usePD(false);
  const [showNote, setShowNote] = usePD(false);
  const [editMode, setEditMode] = usePD(false);
  const [deleteConfirm, setDeleteConfirm] = usePD(false);
  const [tlFilter, setTlFilter] = usePD("all");
  const [showAddLink, setShowAddLink] = usePD(false);
  const [linkLabel, setLinkLabel] = usePD("");
  const [linkUrl, setLinkUrl] = usePD("");
  const [savingLink, setSavingLink] = usePD(false);
  const [showAddBlocker, setShowAddBlocker] = usePD(false);
  const [blockerDesc, setBlockerDesc] = usePD("");
  const [blockerTipo, setBlockerTipo] = usePD("otro");
  const [savingBlocker, setSavingBlocker] = usePD(false);
  const [editStructureText, setEditStructureText] = usePD(false);
  const [structureText, setStructureText] = usePD(project.structureText || "");
  const [savingStructure, setSavingStructure] = usePD(false);
  const [uploadingImage, setUploadingImage] = usePD(false);
  const [expandedTaskId, setExpandedTaskId] = usePD(null);
  const [newSubtarea, setNewSubtarea] = usePD("");
  const [editBilling, setEditBilling] = usePD(false);
  const [billingTarifa, setBillingTarifa] = usePD(String(project.tarifaHora || ""));
  const [billingPresup, setBillingPresup] = usePD(String(project.presupuesto || ""));
  const [savingBilling, setSavingBilling] = usePD(false);
  const [showAddTask, setShowAddTask] = usePD(false);
  const [newTaskType, setNewTaskType] = usePD("task");
  const [newTaskDesc, setNewTaskDesc] = usePD("");
  const [newTaskWith, setNewTaskWith] = usePD("");
  const [newTaskDate, setNewTaskDate] = usePD("");
  const [newTaskDateStart, setNewTaskDateStart] = usePD("");
  const [newTaskPrepFile, setNewTaskPrepFile] = usePD(null);
  const [savingNewTask, setSavingNewTask] = usePD(false);
  const [editingTaskId, setEditingTaskId] = usePD(null);
  const [editTaskDesc, setEditTaskDesc] = usePD("");
  const [editTaskDate, setEditTaskDate] = usePD("");
  const [editTaskDateStart, setEditTaskDateStart] = usePD("");
  const [editTaskPriority, setEditTaskPriority] = usePD("media");
  const [savingEditTask, setSavingEditTask] = usePD(false);
  const [confirmDeleteTaskId, setConfirmDeleteTaskId] = usePD(null);

  const startEditTask = (t) => {
    setEditingTaskId(t.id);
    setEditTaskDesc(t.name || "");
    setEditTaskDate(t.fechaVencimiento || "");
    setEditTaskDateStart(t.fechaInicio || "");
    setEditTaskPriority(t.priority || "media");
  };

  const saveEditTask = async (t) => {
    setSavingEditTask(true);
    try {
      await D_pd.API.updateTask(project.id, t.id, {
        descripcion: editTaskDesc.trim() || t.name,
        fecha_inicio: editTaskDateStart || null,
        fecha_vencimiento: editTaskDate || null,
        prioridad: editTaskPriority,
      });
      setEditingTaskId(null);
      // Recargar proyecto
      window.dispatchEvent(new CustomEvent("maestro:reloadProject", { detail: { projectId: project.id } }));
    } catch(e) { alert("Error al guardar: " + e.message); }
    finally { setSavingEditTask(false); }
  };

  // ── Google integration state ────────────────────────────────────────
  const [googleEnabled, setGoogleEnabled] = usePD(null); // null=loading, true/false
  const [driveFolder, setDriveFolder] = usePD(null);
  const [driveLoading, setDriveLoading] = usePD(false);
  const [calendarSyncing, setCalendarSyncing] = usePD(false);
  const [calendarEventId, setCalendarEventId] = usePD(project.calendarEventId || null);
  const [googleMsg, setGoogleMsg] = usePD(null);

  usePDE(() => {
    D_pd.API.googleStatus().then(s => setGoogleEnabled(s.enabled)).catch(() => setGoogleEnabled(false));
    if (project.driveFolderId) setDriveFolder({ folder_id: project.driveFolderId, folder_url: `https://drive.google.com/drive/folders/${project.driveFolderId}` });
  }, [project.id]);

  const handleDriveOpen = async () => {
    if (driveFolder) { window.open(driveFolder.folder_url, "_blank"); return; }
    setDriveLoading(true); setGoogleMsg(null);
    try {
      const f = await D_pd.API.googleDriveFolder(project.id);
      setDriveFolder(f);
      if (f.folder_url) window.open(f.folder_url, "_blank");
    } catch(e) { setGoogleMsg("Error: " + e.message); }
    finally { setDriveLoading(false); }
  };

  const handleCalendarSync = async () => {
    setCalendarSyncing(true); setGoogleMsg(null);
    try {
      const r = await D_pd.API.googleCalendarSync(project.id);
      setCalendarEventId(r.event_id);
      setGoogleMsg(r.action === "created" ? "✅ Evento creado en Calendar" : "✅ Evento actualizado en Calendar");
    } catch(e) { setGoogleMsg("Error: " + e.message); }
    finally { setCalendarSyncing(false); }
  };

  const handleCalendarDelete = async () => {
    if (!calendarEventId) return;
    setCalendarSyncing(true); setGoogleMsg(null);
    try {
      await D_pd.API.googleCalendarDeleteEvent(calendarEventId, project.id);
      setCalendarEventId(null);
      setGoogleMsg("🗑 Evento eliminado del calendario");
    } catch(e) { setGoogleMsg("Error: " + e.message); }
    finally { setCalendarSyncing(false); }
  };

  usePDE(() => {
    const onEsc = e => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onEsc);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onEsc);
      document.body.style.overflow = "";
    };
  }, []);

  // ── Computed ────────────────────────────────────────────────────────
  const today = usePDM(() => { const d = new Date(); d.setHours(0,0,0,0); return d; }, []);
  const deadlineDate = project.deadline ? new Date(project.deadline) : null;
  const daysLeft = deadlineDate ? Math.ceil((deadlineDate - today) / 86400000) : null;
  const ratio = project.actualHours / (project.estimatedHours || 1);
  const overload = project.actualHours - (project.estimatedHours || 0);
  const uniqueDays = new Set((project.workHours || []).map(w => w.date)).size;
  const activeTasks = project.tasks.filter(t => !t.done).length;
  const activeBlockers = project.blockers.filter(b => !b.resolved).length;

  const timelineEvents = usePDM(() => {
    const all = [...(project.history || [])];
    if (tlFilter === "state") return all.filter(h => h.type === "state");
    if (tlFilter === "hours") return all.filter(h => h.type === "hours" || h.type === "time");
    if (tlFilter === "tasks") return all.filter(h => h.type === "task");
    if (tlFilter === "notes") return all.filter(h => h.type === "note");
    return all;
  }, [project.history, tlFilter]);

  const inStyle = { padding: "7px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 13, width: "100%", boxSizing: "border-box" };

  // ── Edit form state ─────────────────────────────────────────────────
  const [eDesc, setEDesc] = usePD(project.description || "");
  const [ePrio, setEPrio] = usePD(project.priority || "media");
  const [eHours, setEHours] = usePD(String(project.estimatedHours || ""));
  const [eDeadline, setEDeadline] = usePD(project.deadline || "");
  const [eInicio, setEInicio] = usePD(project.fechaInicio || "");
  const [eResp, setEResp] = usePD(project.responsable || "");
  const [eSpecs, setESpecs] = usePD(project.specsText || "");
  const [eSaving, setESaving] = usePD(false);

  const saveEdit = async (e) => {
    e.preventDefault();
    setESaving(true);
    try {
      await onEditProject(project.id, {
        descripcion: eDesc || undefined,
        prioridad: ePrio,
        estimated_hours: eHours ? parseFloat(eHours) : undefined,
        deadline: eDeadline || undefined,
        fecha_inicio: eInicio || undefined,
        responsable: eResp || undefined,
        specs_text: eSpecs || undefined,
      });
      setEditMode(false);
    } finally { setESaving(false); }
  };

  return (
    <div style={{
      height: "100%",
      background: "var(--bg-base)",
      display: "flex", flexDirection: "column",
      overflow: "hidden",
    }}>

      {/* ── TOP BAR ───────────────────────────────────────────────── */}
      <div style={{
        position: "sticky", top: 0, zIndex: 10,
        background: "var(--bg-surface)", borderBottom: "1px solid var(--border)",
        padding: "0 32px", height: 56,
        display: "flex", alignItems: "center", gap: 16,
        boxShadow: "0 1px 8px rgba(0,0,0,0.06)"
      }}>
        <button className="btn btn-ghost" style={{ height: 34, fontSize: 13, gap: 6, display: "flex", alignItems: "center" }} onClick={onClose}>
          {I_pd.arrow ? I_pd.arrow(14) : null} Volver
        </button>
        <div style={{ width: 1, height: 24, background: "var(--border)" }} />
        <div style={{ flex: 1, fontWeight: 600, fontSize: 16 }}>{project.name}</div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {!showHours && !showNote && (
            <>
              <button className="btn btn-ghost" style={{ height: 32, fontSize: 12 }} onClick={() => { setShowHours(true); setShowNote(false); }}>
                + Registrar horas
              </button>
              <button className="btn btn-ghost" style={{ height: 32, fontSize: 12 }} onClick={() => { setShowNote(true); setShowHours(false); }}>
                + Agregar nota
              </button>
              <button className="btn btn-ghost" style={{ height: 32, fontSize: 12 }} onClick={() => setEditMode(e => !e)}>
                {editMode ? "Cerrar edicion" : "Editar"}
              </button>
            </>
          )}
          {onDuplicateProject && (
            <button className="btn btn-ghost" style={{ height: 32, fontSize: 12 }} onClick={() => onDuplicateProject(project.id)} title="Duplicar proyecto">
              Duplicar
            </button>
          )}
          {onArchiveProject && (
            <button className="btn btn-ghost" style={{ height: 32, fontSize: 12, color: project.archived ? "var(--accent)" : "var(--fg-muted)" }}
              onClick={() => onArchiveProject(project.id, project.archived)}
              title={project.archived ? "Desarchivar" : "Archivar proyecto"}>
              {project.archived ? "Desarchivar" : "Archivar"}
            </button>
          )}
          {!deleteConfirm
            ? <button className="btn btn-ghost" style={{ height: 32, fontSize: 12, color: "var(--danger)" }} onClick={() => setDeleteConfirm(true)}>Eliminar</button>
            : <>
                <button className="btn btn-ghost" style={{ height: 32, fontSize: 11, background: "var(--danger)", color: "#fff" }} onClick={async () => { await onDeleteProject(project.id); onClose(); }}>Confirmar eliminar</button>
                <button className="btn btn-ghost" style={{ height: 32, fontSize: 11 }} onClick={() => setDeleteConfirm(false)}>No</button>
              </>
          }
        </div>
      </div>

      {/* ── INLINE FORMS (horas / nota) ───────────────────────────── */}
      {(showHours || showNote) && (
        <div style={{ background: "var(--bg-surface)", borderBottom: "1px solid var(--border)", padding: "0 32px" }}>
          {showHours && <AddHoursForm project={project} onSave={async (h, d) => { await onAddHours(project.id, h, d); setShowHours(false); }} onCancel={() => setShowHours(false)} />}
          {showNote && <AddNoteForm onSave={async (t, tp) => { await onAddNote(project.id, t, tp); setShowNote(false); }} onCancel={() => setShowNote(false)} />}
        </div>
      )}

      {/* ── SCROLLABLE CONTENT ────────────────────────────────────── */}
      <div style={{ flex: 1, overflowY: "auto", padding: "32px", display: "flex", flexDirection: "column", gap: 20, maxWidth: 960, width: "100%", margin: "0 auto", boxSizing: "border-box" }}>

        {/* ── EDIT FORM ──────────────────────────────────────────── */}
        {editMode && (
          <PDCard>
            <PDSectionTitle>Editar proyecto</PDSectionTitle>
            <form onSubmit={saveEdit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div style={{ gridColumn: "1 / -1" }}>
                  <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 4 }}>Descripcion</div>
                  <input value={eDesc} onChange={e => setEDesc(e.target.value)} style={inStyle} />
                </div>
                <div>
                  <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 4 }}>Prioridad</div>
                  <select value={ePrio} onChange={e => setEPrio(e.target.value)} style={inStyle}>
                    <option value="baja">Baja</option>
                    <option value="media">Media</option>
                    <option value="alta">Alta</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 4 }}>Responsable</div>
                  <input value={eResp} onChange={e => setEResp(e.target.value)} placeholder="Alexis" style={inStyle} />
                </div>
                <div>
                  <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 4 }}>Horas estimadas</div>
                  <input type="number" min="0" step="0.5" value={eHours} onChange={e => setEHours(e.target.value)} style={inStyle} />
                </div>
                <div>
                  <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 4 }}>Deadline</div>
                  <input type="date" value={eDeadline} onChange={e => setEDeadline(e.target.value)} style={inStyle} />
                </div>
                <div>
                  <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 4 }}>Fecha de inicio</div>
                  <input type="date" value={eInicio} onChange={e => setEInicio(e.target.value)} style={inStyle} />
                </div>
                <div style={{ gridColumn: "1 / -1" }}>
                  <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 4 }}>Especificaciones tecnicas / Stack</div>
                  <textarea value={eSpecs} onChange={e => setESpecs(e.target.value)} placeholder="Stack, decisiones de arquitectura, APIs usadas..." style={{ ...inStyle, height: 90, resize: "vertical" }} />
                </div>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button type="submit" className="btn btn-primary" style={{ height: 34, fontSize: 13 }} disabled={eSaving}>{eSaving ? "Guardando..." : "Guardar cambios"}</button>
                <button type="button" className="btn btn-ghost" style={{ height: 34, fontSize: 13 }} onClick={() => setEditMode(false)}>Cancelar</button>
              </div>
            </form>
          </PDCard>
        )}

        {/* ── SECCION 1: ENCABEZADO ─────────────────────────────── */}
        <PDCard>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 8 }}>
                <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700 }}>{project.name}</h1>
                <span className={`pcard-priority priority-${project.priority}`} style={{ fontSize: 11 }}>{project.priority.toUpperCase()}</span>
                {project.blocked && <span style={{ fontSize: 11, fontWeight: 700, color: "var(--danger)", background: "rgba(220,38,38,0.1)", borderRadius: 4, padding: "2px 8px" }}>BLOQUEADO</span>}
                {project.archived && <span style={{ fontSize: 11, fontWeight: 700, color: "var(--fg-muted)", background: "var(--bg-subtle)", borderRadius: 4, padding: "2px 8px" }}>ARCHIVADO</span>}
              </div>
              <p style={{ margin: "0 0 12px", color: "var(--fg-muted)", fontSize: 14, lineHeight: 1.5 }}>{project.description}</p>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                <span className="chip" style={{ fontWeight: 600 }}>
                  <span className="chip-dot" style={{ color: "var(--accent)" }} />
                  {D_pd.STATE_LABEL[project.state]}
                </span>
                <span className="chip mono">{project.daysInState}d en estado</span>
                {project.deadline && (
                  <span className="chip mono" style={{
                    color: daysLeft !== null && daysLeft <= 0 ? "var(--danger)" : daysLeft !== null && daysLeft <= 3 ? "var(--warning)" : "inherit",
                    fontWeight: daysLeft !== null && daysLeft <= 3 ? 600 : 400
                  }}>
                    Deadline: {project.deadline}
                    {daysLeft !== null && ` (${daysLeft <= 0 ? Math.abs(daysLeft) + "d vencido" : daysLeft + "d restantes"})`}
                  </span>
                )}
                {project.tags.map(t => <span key={t} className="chip">{t}</span>)}
              </div>
              <div style={{ display: "flex", gap: 20, marginTop: 12, fontSize: 13 }}>
                {project.clientArea && <div><span style={{ color: "var(--fg-subtle)" }}>Area: </span>{project.clientArea}</div>}
                {project.responsable && <div><span style={{ color: "var(--fg-subtle)" }}>Responsable: </span><strong>{project.responsable}</strong></div>}
                {project.fechaInicio && <div><span style={{ color: "var(--fg-subtle)" }}>Inicio: </span>{project.fechaInicio}</div>}
              </div>
            </div>
          </div>
        </PDCard>

        {/* ── SECCION 2: METRICAS ───────────────────────────────── */}
        <PDCard>
          <PDSectionTitle>Metricas</PDSectionTitle>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 24, marginBottom: 16 }}>
            <PDMetric label="Horas estimadas" value={`${project.estimatedHours}h`} />
            <PDMetric
              label="Horas trabajadas"
              value={`${project.actualHours}h`}
              sub={`${Math.round(ratio * 100)}% del estimado`}
              color={ratio > 1.3 ? "var(--danger)" : ratio > 1 ? "var(--warning)" : "var(--success)"}
              large
            />
            {overload > 0 && <PDMetric label="Overload" value={`+${overload.toFixed(1)}h`} sub={`+${Math.round((ratio-1)*100)}% sobre estimado`} color="var(--danger)" />}
            <PDMetric label="Velocity" value={`${project.velocity}h/dia`} sub={`${uniqueDays} dias trabajados`} />
            <PDMetric label="Tareas" value={`${project.tasks.filter(t=>t.done).length}/${project.tasks.length}`} sub={`${activeTasks} pendientes`} />
            {activeBlockers > 0 && <PDMetric label="Bloqueadores" value={activeBlockers} sub="activos" color="var(--danger)" />}
          </div>
          <div className="pcard-bar" style={{ height: 8 }}>
            <div className={`pcard-bar-fill ${ratio > 1.3 ? "over" : ratio > 1 ? "warn" : ""}`} style={{ width: `${Math.min(ratio * 100, 100)}%` }} />
          </div>
          {ratio > 1 && (
            <div style={{ marginTop: 8, fontSize: 12, color: "var(--fg-muted)", fontStyle: "italic" }}>
              A este ritmo ({project.velocity}h/dia), el proyecto ya esta {Math.round((ratio-1)*100)}% por encima del estimado.
              {project.velocity > 0 && overload > 0 && ` Quedan ~${(overload / project.velocity).toFixed(1)} dias de trabajo extra sin presupuestar.`}
            </div>
          )}
        </PDCard>

        {/* ── SECCION 3: ESTADO ACTUAL ──────────────────────────── */}
        <PDCard>
          <PDSectionTitle>Estado actual</PDSectionTitle>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px 32px", fontSize: 14 }}>
            <div>
              <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 3 }}>Estado</div>
              <div style={{ fontWeight: 600, fontSize: 15 }}>{D_pd.STATE_LABEL[project.state]}</div>
              <div style={{ fontSize: 12, color: "var(--fg-muted)", marginTop: 2 }}>Desde hace {project.daysInState} dias</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 3 }}>Bloqueado</div>
              <div style={{ fontWeight: 600, color: project.blocked ? "var(--danger)" : "var(--success)" }}>{project.blocked ? "SI - Hay bloqueos activos" : "NO - Fluye sin problemas"}</div>
            </div>
            {project.statusHistory && project.statusHistory.length >= 2 && (
              <div>
                <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 3 }}>Estado anterior</div>
                <div style={{ fontWeight: 500 }}>{project.statusHistory[1]?.estadoAnterior || "—"}</div>
              </div>
            )}
            <div>
              <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 3 }}>Ultima actualizacion</div>
              <div style={{ fontWeight: 500 }}>{project.lastUpdate}</div>
            </div>
          </div>
          {/* Cambio de estado rapido */}
          <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
            <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 8 }}>Cambiar estado:</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {D_pd.STATES.map(s => s !== project.state && (
                <button key={s} className="btn btn-ghost" style={{ height: 30, fontSize: 12, padding: "0 12px" }}
                  onClick={() => onChangeState(project.id, s)}>
                  -> {D_pd.STATE_LABEL_SHORT[s]}
                </button>
              ))}
            </div>
          </div>
        </PDCard>

        {/* ── SECCION 4: TAREAS ────────────────────────────────── */}
        <PDCard>
          <div style={{ display: "flex", alignItems: "center", marginBottom: 16 }}>
            <PDSectionTitle>
              Tareas ({project.tasks.filter(t=>t.done).length} completadas / {project.tasks.length} total)
              {" "}{activeTasks > 0 && <span style={{ color: "var(--accent)", fontWeight: 500 }}>{activeTasks} pendientes</span>}
            </PDSectionTitle>
            {onAddTask && (
              <button className="btn btn-ghost" style={{ height: 24, fontSize: 11, padding: "0 10px", marginLeft: "auto" }}
                onClick={() => { setShowAddTask(v => !v); setNewTaskDesc(""); setNewTaskWith(""); setNewTaskDate(""); setNewTaskType("task"); setNewTaskPrepFile(null); }}>
                {showAddTask ? "Cancelar" : "+ Nueva tarea"}
              </button>
            )}
          </div>
          {showAddTask && onAddTask && (
            <div style={{ marginBottom: 16, padding: "14px 16px", background: "var(--bg-base)", borderRadius: "var(--r-md)", border: "1px solid var(--border)" }}>
              <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
                {[["task","Tarea"], ["meeting","Reunión"], ["event","Evento"]].map(([v,l]) => (
                  <button key={v} className={`btn ${newTaskType === v ? "btn-primary" : "btn-ghost"}`}
                    style={{ height: 28, fontSize: 12 }} onClick={() => setNewTaskType(v)}>{l}</button>
                ))}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <input value={newTaskDesc} onChange={e => setNewTaskDesc(e.target.value)}
                  placeholder={newTaskType === "meeting" ? "De qué se trata la reunión…" : newTaskType === "event" ? "Nombre del evento…" : "Descripción de la tarea…"}
                  style={{ ...inStyle }} autoFocus />
                {newTaskType === "meeting" && (
                  <>
                    <input value={newTaskWith} onChange={e => setNewTaskWith(e.target.value)}
                      placeholder="Con quién (ej: Juan Pérez, cliente ACME)" style={{ ...inStyle }} />
                    <input type="file" accept=".pdf,.doc,.docx,.txt,.md,.pptx,.xlsx,.png,.jpg"
                      style={{ fontSize: 12, color: "var(--text-primary)" }}
                      onChange={e => setNewTaskPrepFile(e.target.files[0] || null)} />
                  </>
                )}
                <div style={{ display: "flex", gap: 8 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 3 }}>Fecha de inicio</div>
                    <input type="date" value={newTaskDateStart} onChange={e => setNewTaskDateStart(e.target.value)} style={{ ...inStyle, width: "100%", boxSizing: "border-box" }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 3 }}>
                      {newTaskType === "meeting" ? "Fecha de reunión" : newTaskType === "event" ? "Fecha del evento" : "Fecha de vencimiento"}
                    </div>
                    <input type="date" value={newTaskDate} onChange={e => setNewTaskDate(e.target.value)} style={{ ...inStyle, width: "100%", boxSizing: "border-box" }} />
                  </div>
                </div>
                <button className="btn btn-primary" style={{ height: 34, fontSize: 13, alignSelf: "flex-end" }}
                  disabled={savingNewTask || !newTaskDesc.trim()}
                  onClick={async () => {
                    if (!newTaskDesc.trim()) return;
                    setSavingNewTask(true);
                    try {
                      await onAddTask({
                        projectId: project.id,
                        taskName: newTaskDesc.trim(),
                        taskType: newTaskType,
                        meetingWith: newTaskWith.trim() || null,
                        fechaInicio: newTaskDateStart || null,
                        fechaVencimiento: newTaskDate || null,
                        prepFile: newTaskPrepFile || null,
                      });
                      setShowAddTask(false); setNewTaskDesc(""); setNewTaskWith(""); setNewTaskDate(""); setNewTaskDateStart(""); setNewTaskType("task"); setNewTaskPrepFile(null);
                    } finally { setSavingNewTask(false); }
                  }}>
                  {savingNewTask ? "..." : newTaskType === "meeting" ? "Crear reunión" : newTaskType === "event" ? "Crear evento" : "Crear tarea"}
                </button>
              </div>
            </div>
          )}
          {project.tasks.length === 0
            ? <div style={{ fontSize: 13, color: "var(--fg-subtle)", fontStyle: "italic", padding: "8px 0" }}>Sin tareas todavia. El asistente puede crearte tareas si le describis el proyecto.</div>
            : <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {project.tasks.map(t => {
                  const td = t.fechaVencimiento ? new Date(t.fechaVencimiento) : null;
                  const tdl = td ? Math.ceil((td - today) / 86400000) : null;
                  const icon = t.done ? "V" : t.inProgress ? ">" : "[ ]";
                  const iconColor = t.done ? "var(--success)" : t.inProgress ? "var(--accent)" : "var(--fg-subtle)";
                  const isExpanded = expandedTaskId === t.id;
                  const subtareas = t.subtareas || [];
                  const isActiveTimer = activeTimer && activeTimer.taskId === t.id;
                  const taskElapsed = isActiveTimer ? timerDisplaySeconds : (t.elapsedSeconds || 0);
                  const isMeeting = t.taskType === "meeting";
                  return (
                    <div key={t.id} style={{ borderRadius: "var(--r-md)", background: "var(--bg-base)", border: `1px solid ${isActiveTimer ? "var(--accent)" : isMeeting ? "rgba(var(--accent-h),0.2)" : "var(--border)"}`, opacity: t.done ? 0.75 : 1, overflow: "hidden" }}>
                      <div style={{ display: "flex", gap: 12, alignItems: "flex-start", padding: "12px 16px", cursor: "pointer" }}
                        onClick={() => onToggleTask(project.id, t.id)}>
                        <div style={{ fontSize: 15, color: isMeeting ? "var(--accent)" : iconColor, minWidth: 24, fontWeight: 700, marginTop: 1, fontFamily: "monospace" }}>
                          {isMeeting ? I_pd.meeting(15) : icon}
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 500, fontSize: 14, textDecoration: t.done ? "line-through" : "none", color: t.done ? "var(--fg-muted)" : "var(--text-primary)" }}>{t.name}</div>
                          {isMeeting && (
                            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 4, fontSize: 12 }}>
                              {t.meetingWith && <span style={{ color: "var(--fg-muted)", display: "flex", alignItems: "center", gap: 3 }}>{I_pd.users ? I_pd.users(11) : "👥"} {t.meetingWith}</span>}
                              {t.meetingPrepUrl && (
                                <a href={t.meetingPrepUrl} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}
                                  style={{ color: "var(--accent)", textDecoration: "none" }}>
                                  📎 {t.meetingPrepFilename || "Archivo prep"}
                                </a>
                              )}
                              {!t.meetingPrepUrl && onUploadTaskPrepFile && !t.done && (
                                <label style={{ color: "var(--fg-subtle)", cursor: "pointer" }} onClick={e => e.stopPropagation()}>
                                  <input type="file" style={{ display: "none" }} accept=".pdf,.doc,.docx,.txt,.md,.pptx,.xlsx,.png,.jpg"
                                    onChange={async e => { const f = e.target.files[0]; if (f) { await onUploadTaskPrepFile(project.id, t.id, f); e.target.value = ""; } }} />
                                  <span style={{ fontSize: 11, borderBottom: "1px dashed var(--fg-subtle)" }}>+ Subir prep</span>
                                </label>
                              )}
                            </div>
                          )}
                          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 4, fontSize: 12, color: "var(--fg-subtle)" }}>
                            {!isMeeting && <span style={{ fontWeight: 600, color: PD_PRIORITY_COLOR[t.priority], textTransform: "uppercase", fontSize: 10 }}>{t.priority}</span>}
                            {t.estimated && <span>{t.estimated}h estimado</span>}
                            {subtareas.length > 0 && <span style={{ color: "var(--accent)" }}>{subtareas.filter(s=>s.done).length}/{subtareas.length} subtareas</span>}
                            {taskElapsed > 0 && (
                              <span style={{ color: isActiveTimer ? "var(--accent)" : "var(--fg-muted)", fontFamily: "monospace", fontWeight: isActiveTimer ? 700 : 400 }}>
                                {isActiveTimer && "▶ "}{fmtTimer(taskElapsed)}
                              </span>
                            )}
                            {td && !t.done && (
                              <span style={{ color: tdl <= 0 ? "var(--danger)" : tdl <= 1 ? "var(--warning)" : "inherit", fontWeight: tdl <= 1 ? 600 : 400 }}>
                                Vence: {tdl <= 0 ? `VENCIDA hace ${Math.abs(tdl)}d` : tdl === 0 ? "HOY" : tdl === 1 ? "MANANA" : t.fechaVencimiento}
                              </span>
                            )}
                            {t.done && t.completedAt && <span style={{ color: "var(--success)" }}>Completada: {new Date(t.completedAt).toLocaleDateString("es-AR")}</span>}
                          </div>
                        </div>
                        {onStartTimer && !t.done && (
                          <button
                            className="btn btn-ghost"
                            style={{ height: 24, fontSize: 13, padding: "0 8px", flexShrink: 0, color: isActiveTimer ? "var(--accent)" : "var(--fg-muted)" }}
                            title={isActiveTimer ? "Pausar timer" : "Iniciar timer"}
                            onClick={e => {
                              e.stopPropagation();
                              if (isActiveTimer) onPauseTimer();
                              else onStartTimer(project.id, t.id);
                            }}>
                            {isActiveTimer ? "⏸" : "▶"}
                          </button>
                        )}
                        {!t.done && (
                          <button className="btn btn-ghost" style={{ height: 24, fontSize: 11, padding: "0 8px", flexShrink: 0, color: editingTaskId === t.id ? "var(--accent)" : "var(--fg-muted)" }}
                            title="Editar tarea"
                            onClick={e => { e.stopPropagation(); editingTaskId === t.id ? setEditingTaskId(null) : startEditTask(t); }}>
                            ✏️
                          </button>
                        )}
                        {confirmDeleteTaskId === t.id
                          ? <button className="btn btn-ghost" style={{ height: 24, fontSize: 11, padding: "0 8px", flexShrink: 0, color: "var(--danger)", border: "1px solid var(--danger)", fontWeight: 700 }}
                              onClick={async e => {
                                e.stopPropagation();
                                setConfirmDeleteTaskId(null);
                                try {
                                  await D_pd.API.deleteTask(project.id, t.id);
                                  window.dispatchEvent(new CustomEvent("maestro:reloadProject", { detail: { projectId: project.id } }));
                                } catch(err) { alert("Error al eliminar: " + err.message); }
                              }}>
                              ¿Seguro?
                            </button>
                          : <button className="btn btn-ghost" style={{ height: 24, fontSize: 11, padding: "0 8px", flexShrink: 0, color: "var(--danger)" }}
                              title="Eliminar tarea"
                              onClick={e => { e.stopPropagation(); setConfirmDeleteTaskId(t.id); setTimeout(() => setConfirmDeleteTaskId(null), 3000); }}>
                              🗑️
                            </button>
                        }
                        {onUpdateTaskSubtasks && (
                          <button className="btn btn-ghost" style={{ height: 24, fontSize: 11, padding: "0 8px", flexShrink: 0 }}
                            onClick={e => { e.stopPropagation(); setExpandedTaskId(isExpanded ? null : t.id); setNewSubtarea(""); }}>
                            {isExpanded ? "▲" : "▼"} Sub
                          </button>
                        )}
                      </div>
                      {isExpanded && onUpdateTaskSubtasks && (
                        <div style={{ borderTop: "1px solid var(--border)", padding: "10px 16px", background: "var(--bg-surface)" }}>
                          <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 8, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Subtareas</div>
                          {subtareas.map((s, si) => (
                            <div key={si} style={{ display: "flex", gap: 8, alignItems: "center", padding: "5px 0", borderBottom: si < subtareas.length - 1 ? "1px solid var(--border)" : "none" }}>
                              <div style={{ width: 14, height: 14, borderRadius: 3, border: `2px solid ${s.done ? "var(--success)" : "var(--border)"}`, background: s.done ? "var(--success)" : "transparent", cursor: "pointer", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center" }}
                                onClick={() => {
                                  const updated = subtareas.map((x, xi) => xi === si ? { ...x, done: !x.done } : x);
                                  onUpdateTaskSubtasks(project.id, t.id, updated);
                                }}>
                                {s.done && <span style={{ color: "#fff", fontSize: 9, fontWeight: 700 }}>V</span>}
                              </div>
                              <span style={{ flex: 1, fontSize: 13, textDecoration: s.done ? "line-through" : "none", color: s.done ? "var(--fg-subtle)" : "var(--text-primary)" }}>{s.text}</span>
                              <button style={{ background: "none", border: "none", color: "var(--danger)", cursor: "pointer", fontSize: 13, padding: "0 4px" }}
                                onClick={() => {
                                  const updated = subtareas.filter((_, xi) => xi !== si);
                                  onUpdateTaskSubtasks(project.id, t.id, updated);
                                }}>×</button>
                            </div>
                          ))}
                          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                            <input
                              value={newSubtarea}
                              onChange={e => setNewSubtarea(e.target.value)}
                              onKeyDown={e => {
                                if (e.key === "Enter" && newSubtarea.trim()) {
                                  onUpdateTaskSubtasks(project.id, t.id, [...subtareas, { text: newSubtarea.trim(), done: false }]);
                                  setNewSubtarea("");
                                }
                              }}
                              placeholder="Nueva subtarea... (Enter para agregar)"
                              style={{ flex: 1, padding: "5px 8px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 12 }}
                            />
                            <button className="btn btn-ghost" style={{ height: 28, fontSize: 11 }}
                              onClick={() => {
                                if (!newSubtarea.trim()) return;
                                onUpdateTaskSubtasks(project.id, t.id, [...subtareas, { text: newSubtarea.trim(), done: false }]);
                                setNewSubtarea("");
                              }}>+ Agregar</button>
                          </div>
                        </div>
                      )}
                      {editingTaskId === t.id && (
                        <div style={{ borderTop: "1px solid var(--accent)", padding: "12px 16px", background: "var(--bg-surface)" }}
                          onClick={e => e.stopPropagation()}>
                          <div style={{ fontSize: 11, color: "var(--accent)", marginBottom: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>Editar tarea</div>
                          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                            <input value={editTaskDesc} onChange={e => setEditTaskDesc(e.target.value)}
                              placeholder="Descripción"
                              style={{ padding: "6px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 13 }} />
                            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                              <div style={{ display: "flex", flexDirection: "column", gap: 3, flex: 1 }}>
                                <label style={{ fontSize: 11, color: "var(--fg-subtle)" }}>Fecha inicio</label>
                                <input type="date" value={editTaskDateStart} onChange={e => setEditTaskDateStart(e.target.value)}
                                  style={{ padding: "6px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 13 }} />
                              </div>
                              <div style={{ display: "flex", flexDirection: "column", gap: 3, flex: 1 }}>
                                <label style={{ fontSize: 11, color: "var(--fg-subtle)" }}>Fecha vencimiento</label>
                                <input type="date" value={editTaskDate} onChange={e => setEditTaskDate(e.target.value)}
                                  style={{ padding: "6px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 13 }} />
                              </div>
                              {!t.taskType || t.taskType === "task" ? (
                                <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                                  <label style={{ fontSize: 11, color: "var(--fg-subtle)" }}>Prioridad</label>
                                  <select value={editTaskPriority} onChange={e => setEditTaskPriority(e.target.value)}
                                    style={{ padding: "6px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 13 }}>
                                    <option value="alta">Alta</option>
                                    <option value="media">Media</option>
                                    <option value="baja">Baja</option>
                                  </select>
                                </div>
                              ) : null}
                            </div>
                            {editTaskDate && <div style={{ fontSize: 11, color: "var(--fg-subtle)" }}>💡 Guardar con fecha sincronizará automáticamente con Google Calendar</div>}
                            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                              <button className="btn btn-ghost" style={{ height: 28, fontSize: 12 }} onClick={() => setEditingTaskId(null)}>Cancelar</button>
                              <button className="btn btn-primary" style={{ height: 28, fontSize: 12 }} disabled={savingEditTask} onClick={() => saveEditTask(t)}>
                                {savingEditTask ? "Guardando..." : "Guardar"}
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
          }
        </PDCard>

        {/* ── SECCION 5: BLOQUEOS ───────────────────────────────── */}
        <PDCard>
          <div style={{ display: "flex", alignItems: "center", marginBottom: 16 }}>
            <PDSectionTitle>
              Bloqueos / Impedimentos ({project.blockers.filter(b=>!b.resolved).length} activos · {project.blockers.filter(b=>b.resolved).length} resueltos)
            </PDSectionTitle>
            <button className="btn btn-ghost" style={{ height: 24, fontSize: 11, padding: "0 10px", marginLeft: "auto", flexShrink: 0 }}
              onClick={() => { setShowAddBlocker(v => !v); setBlockerDesc(""); setBlockerTipo("otro"); }}>
              {showAddBlocker ? "Cancelar" : "+ Agregar bloqueo"}
            </button>
          </div>
          {showAddBlocker && (
            <form style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}
              onSubmit={async e => {
                e.preventDefault();
                if (!blockerDesc.trim()) return;
                setSavingBlocker(true);
                try {
                  await onAddBlocker(project.id, blockerDesc.trim(), blockerTipo);
                  setShowAddBlocker(false); setBlockerDesc(""); setBlockerTipo("otro");
                } finally { setSavingBlocker(false); }
              }}>
              <input placeholder="Descripcion del bloqueo..." value={blockerDesc} onChange={e => setBlockerDesc(e.target.value)}
                style={{ ...inStyle, flex: 1, minWidth: 200 }} autoFocus />
              <select value={blockerTipo} onChange={e => setBlockerTipo(e.target.value)} style={{ ...inStyle, width: 160 }}>
                <option value="esperando cliente">Esperando cliente</option>
                <option value="sin acceso">Sin acceso</option>
                <option value="tecnico">Tecnico</option>
                <option value="otro">Otro</option>
              </select>
              <button type="submit" className="btn btn-primary" style={{ height: 34, fontSize: 13 }} disabled={savingBlocker}>
                {savingBlocker ? "..." : "Guardar"}
              </button>
            </form>
          )}
          {project.blockers.length === 0 && !showAddBlocker
            ? <div style={{ fontSize: 13, color: "var(--fg-subtle)", fontStyle: "italic", padding: "8px 0" }}>Sin bloqueadores. El proyecto fluye sin problemas.</div>
            : <>
                {project.blockers.filter(b => !b.resolved).length > 0 && (
                  <div style={{ fontSize: 12, color: "var(--fg-subtle)", marginBottom: 12 }}>
                    {project.blockers.filter(b => !b.resolved).length} bloqueadores activos
                    {project.blockers.filter(b => !b.resolved).some(b => b.days > 3) && " — ALERTA: hay bloqueos de mas de 3 dias"}
                  </div>
                )}
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {project.blockers.map(b => {
                    const bc = PD_BLOCKER_COLOR[b.type] || "var(--fg-subtle)";
                    return (
                      <div key={b.id} style={{
                        padding: "12px 16px", borderRadius: "var(--r-md)", fontSize: 13,
                        background: b.resolved ? "var(--bg-base)" : "rgba(220,38,38,0.04)",
                        border: `1px solid ${b.resolved ? "var(--border)" : "rgba(220,38,38,0.2)"}`,
                        borderLeft: `4px solid ${bc}`,
                        opacity: b.resolved ? 0.7 : 1
                      }}>
                        <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 6 }}>
                          <span style={{ fontWeight: 700, fontSize: 12 }}>{b.resolved ? "V" : "X"}</span>
                          <span style={{ fontWeight: 600, flex: 1, fontSize: 14 }}>{b.desc}</span>
                          <span style={{ fontSize: 10, fontWeight: 700, color: bc, textTransform: "uppercase", border: `1px solid ${bc}`, borderRadius: 3, padding: "1px 6px" }}>{b.type}</span>
                        </div>
                        <div style={{ display: "flex", gap: 16, fontSize: 12, color: "var(--fg-subtle)" }}>
                          {b.createdAt && <span>Creado: {new Date(b.createdAt).toLocaleDateString("es-AR")}</span>}
                          {b.resolved && b.resolvedAt
                            ? <span style={{ color: "var(--success)" }}>Resuelto: {new Date(b.resolvedAt).toLocaleDateString("es-AR")}</span>
                            : !b.resolved && b.days > 0 && <span style={{ color: "var(--danger)", fontWeight: 600 }}>{b.days} dias sin resolver</span>
                          }
                        </div>
                        {!b.resolved && (
                          <button className="btn btn-ghost" style={{ height: 26, fontSize: 11, marginTop: 8 }}
                            onClick={() => onResolveBlocker(project.id, b.id)}>
                            Marcar como resuelto
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </>
          }
        </PDCard>

        {/* ── SECCION 6: TIMELINE ───────────────────────────────── */}
        <PDCard>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <PDSectionTitle>Timeline / Historico</PDSectionTitle>
            <div style={{ display: "flex", gap: 6, marginLeft: "auto" }}>
              {[["all","Todo"], ["state","Estados"], ["hours","Horas"], ["tasks","Tareas"], ["notes","Notas"]].map(([v,l]) => (
                <button key={v} className={`btn ${tlFilter === v ? "btn-primary" : "btn-ghost"}`}
                  style={{ height: 24, fontSize: 11, padding: "0 8px" }}
                  onClick={() => setTlFilter(v)}>{l}</button>
              ))}
            </div>
          </div>
          {timelineEvents.length === 0
            ? <div style={{ fontSize: 13, color: "var(--fg-subtle)", fontStyle: "italic", padding: "8px 0" }}>Sin actividad registrada en esta categoria.</div>
            : <div style={{ display: "flex", flexDirection: "column" }}>
                {timelineEvents.map((h, i) => {
                  const dotColor = h.type === "state" ? "var(--accent)" : h.type === "hours" || h.type === "time" ? "var(--success)" : h.type === "note" ? "var(--warning)" : h.type === "blocker" ? "var(--danger)" : "var(--fg-subtle)";
                  return (
                    <div key={i} style={{ display: "flex", gap: 12, padding: "10px 0", borderBottom: i < timelineEvents.length - 1 ? "1px solid var(--border)" : "none" }}>
                      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", minWidth: 70 }}>
                        <div style={{ fontSize: 11, color: "var(--fg-subtle)", fontFamily: "monospace", marginBottom: 4, textAlign: "center" }}>{h.time}</div>
                        <div style={{ width: 10, height: 10, borderRadius: "50%", background: dotColor, flexShrink: 0 }} />
                      </div>
                      <div style={{ flex: 1, paddingTop: 1 }}>
                        <div style={{ fontSize: 13, fontWeight: h.type === "state" ? 600 : 400 }}>{h.text}</div>
                        <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginTop: 2, textTransform: "uppercase", letterSpacing: "0.04em" }}>{h.type}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
          }
        </PDCard>

        {/* ── SECCION 7: CONTEXTO Y RECURSOS ───────────────────── */}
        <PDCard>
          <PDSectionTitle>Contexto y Recursos</PDSectionTitle>

          {/* Links */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--fg-muted)" }}>Links y Referencias</div>
              <button className="btn btn-ghost" style={{ height: 22, fontSize: 11, padding: "0 8px", marginLeft: "auto" }}
                onClick={() => { setShowAddLink(v => !v); setLinkLabel(""); setLinkUrl(""); }}>
                {showAddLink ? "Cancelar" : "+ Agregar link"}
              </button>
            </div>
            {showAddLink && (
              <form style={{ display: "flex", gap: 8, marginBottom: 10, flexWrap: "wrap" }}
                onSubmit={async e => {
                  e.preventDefault();
                  if (!linkUrl.trim()) return;
                  setSavingLink(true);
                  const newLinks = [...(project.links || []), { label: linkLabel.trim() || linkUrl.trim(), url: linkUrl.trim() }];
                  try { await onEditProject(project.id, { links_json: JSON.stringify(newLinks) }); setShowAddLink(false); setLinkLabel(""); setLinkUrl(""); }
                  finally { setSavingLink(false); }
                }}>
                <input placeholder="Etiqueta (ej. Figma)" value={linkLabel} onChange={e => setLinkLabel(e.target.value)} style={{ ...inStyle, width: 130 }} />
                <input placeholder="URL" value={linkUrl} onChange={e => setLinkUrl(e.target.value)} style={{ ...inStyle, flex: 1, minWidth: 180 }} autoFocus />
                <button type="submit" className="btn btn-primary" style={{ height: 34, fontSize: 12 }} disabled={savingLink}>{savingLink ? "..." : "Guardar"}</button>
              </form>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {project.githubUrl && (
                <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderRadius: "var(--r-md)", background: "var(--bg-base)", border: "1px solid var(--border)", fontSize: 13 }}>
                  {I_pd.link ? I_pd.link(14) : null}
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600 }}>GitHub</div>
                    <a href={project.githubUrl} target="_blank" rel="noopener noreferrer" style={{ fontSize: 11, color: "var(--accent)", textDecoration: "none" }}>{project.githubUrl}</a>
                  </div>
                </div>
              )}
              {(project.links || []).map((l, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderRadius: "var(--r-md)", background: "var(--bg-base)", border: "1px solid var(--border)", fontSize: 13 }}>
                  {I_pd.link ? I_pd.link(14) : null}
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600 }}>{l.label}</div>
                    <a href={l.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 11, color: "var(--accent)", textDecoration: "none" }}>{l.url}</a>
                  </div>
                  <button className="btn btn-ghost" style={{ height: 22, fontSize: 11, padding: "0 8px", color: "var(--danger)" }}
                    onClick={async () => {
                      const updated = (project.links || []).filter((_, j) => j !== i);
                      await onEditProject(project.id, { links_json: JSON.stringify(updated) });
                    }}>×</button>
                </div>
              ))}
              {!project.githubUrl && !(project.links || []).length && !showAddLink && (
                <div style={{ fontSize: 13, color: "var(--fg-subtle)", fontStyle: "italic" }}>Sin links. Hacé click en "+ Agregar link" para añadir referencias.</div>
              )}
            </div>
          </div>

          {/* Google Drive + Calendar */}
          {googleEnabled && (
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--fg-muted)", marginBottom: 10 }}>Google</div>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
                {/* Drive */}
                <button className="btn btn-secondary" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}
                  onClick={handleDriveOpen} disabled={driveLoading}>
                  <span style={{ fontSize: 14 }}>📁</span>
                  {driveLoading ? "Abriendo..." : driveFolder ? "Ver carpeta en Drive" : "Crear carpeta en Drive"}
                </button>

                {/* Calendar sync */}
                {project.deadline ? (
                  <>
                    <button className="btn btn-secondary" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}
                      onClick={handleCalendarSync} disabled={calendarSyncing}>
                      <span style={{ fontSize: 14 }}>📅</span>
                      {calendarSyncing ? "Sincronizando..." : calendarEventId ? "Actualizar en Calendar" : "Agregar deadline a Calendar"}
                    </button>
                    {calendarEventId && (
                      <button className="btn btn-ghost" style={{ fontSize: 11, color: "var(--danger)", padding: "0 8px", height: 28 }}
                        onClick={handleCalendarDelete} disabled={calendarSyncing} title="Eliminar evento del calendario">
                        🗑
                      </button>
                    )}
                  </>
                ) : (
                  <span style={{ fontSize: 12, color: "var(--fg-subtle)", fontStyle: "italic" }}>Definí un deadline para sincronizar con Calendar</span>
                )}
              </div>
              {googleMsg && (
                <div style={{ marginTop: 8, fontSize: 12, color: googleMsg.startsWith("Error") ? "var(--danger)" : "var(--success)" }}>
                  {googleMsg}
                </div>
              )}
            </div>
          )}

          {/* Especificaciones tecnicas */}
          {project.specsText && (
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--fg-muted)", marginBottom: 8 }}>Especificaciones Tecnicas / Stack</div>
              <div style={{ padding: "12px 16px", borderRadius: "var(--r-md)", background: "var(--bg-base)", border: "1px solid var(--border)", fontSize: 13, lineHeight: 1.7, whiteSpace: "pre-wrap", color: "var(--text-primary)" }}>
                {project.specsText}
              </div>
            </div>
          )}

          {/* Notas, Learnings, Decisiones */}
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: "var(--fg-muted)", marginBottom: 8 }}>Notas, Decisiones y Aprendizajes ({project.notes.length})</div>
            {project.notes.length === 0
              ? <div style={{ fontSize: 13, color: "var(--fg-subtle)", fontStyle: "italic" }}>Sin notas todavia.</div>
              : <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {project.notes.slice().reverse().map((n, i) => (
                    <div key={n.id || i} style={{ padding: "12px 16px", borderRadius: "var(--r-md)", background: "var(--bg-base)", border: "1px solid var(--border)", borderLeft: `4px solid ${PD_NOTE_COLOR[n.type] || "var(--fg-subtle)"}` }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                        <span style={{ fontSize: 10, fontWeight: 700, color: PD_NOTE_COLOR[n.type], textTransform: "uppercase", letterSpacing: "0.06em", border: `1px solid ${PD_NOTE_COLOR[n.type]}`, borderRadius: 3, padding: "1px 6px" }}>
                          {PD_NOTE_ICON[n.type] || "Nota"}
                        </span>
                        <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--fg-subtle)" }}>{n.date}</span>
                      </div>
                      <div style={{ fontSize: 14, lineHeight: 1.6 }}>{n.text}</div>
                    </div>
                  ))}
                </div>
            }
          </div>
        </PDCard>

        {/* ── SECCION 7.5: ESTRUCTURA DE LA APLICACION ─────────── */}
        <PDCard>
          <PDSectionTitle>Estructura de la Aplicación</PDSectionTitle>

          {/* Texto estructurado */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--fg-muted)" }}>Descripción textual</div>
              {!editStructureText && (
                <button className="btn btn-ghost" style={{ height: 22, fontSize: 11, padding: "0 8px", marginLeft: "auto" }}
                  onClick={() => { setEditStructureText(true); setStructureText(project.structureText || ""); }}>
                  {project.structureText ? "Editar" : "+ Agregar texto"}
                </button>
              )}
            </div>
            {editStructureText ? (
              <div>
                <textarea
                  value={structureText}
                  onChange={e => setStructureText(e.target.value)}
                  placeholder={"src/\n  components/\n    Header.jsx\n  pages/\n    Home.jsx\nbackend/\n  app/\n    main.py"}
                  style={{ ...inStyle, height: 200, resize: "vertical", fontFamily: "monospace", fontSize: 12, lineHeight: 1.6 }}
                  autoFocus
                />
                <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                  <button className="btn btn-primary" style={{ height: 32, fontSize: 12 }}
                    disabled={savingStructure}
                    onClick={async () => {
                      setSavingStructure(true);
                      try {
                        await onEditProject(project.id, { structure_text: structureText || null });
                        setEditStructureText(false);
                      } finally { setSavingStructure(false); }
                    }}>
                    {savingStructure ? "Guardando..." : "Guardar"}
                  </button>
                  <button className="btn btn-ghost" style={{ height: 32, fontSize: 12 }}
                    onClick={() => { setEditStructureText(false); setStructureText(project.structureText || ""); }}>
                    Cancelar
                  </button>
                </div>
              </div>
            ) : project.structureText ? (
              <pre style={{ padding: "12px 16px", borderRadius: "var(--r-md)", background: "var(--bg-base)", border: "1px solid var(--border)", fontSize: 12, lineHeight: 1.7, overflowX: "auto", color: "var(--text-primary)", margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", fontFamily: "monospace" }}>
                {project.structureText}
              </pre>
            ) : (
              <div style={{ fontSize: 13, color: "var(--fg-subtle)", fontStyle: "italic" }}>Sin estructura de texto. Hacé click en "+ Agregar texto" para documentar el árbol de archivos o arquitectura.</div>
            )}
          </div>

          {/* Imagen */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--fg-muted)" }}>Imagen (diagrama, captura, esquema)</div>
              <label style={{ marginLeft: "auto", cursor: uploadingImage ? "default" : "pointer" }}>
                <input type="file" accept="image/*" style={{ display: "none" }}
                  disabled={uploadingImage}
                  onChange={async e => {
                    const file = e.target.files[0];
                    if (!file) return;
                    setUploadingImage(true);
                    try {
                      const updated = await onUploadStructureImage(project.id, file);
                    } catch (err) {
                      alert("Error al subir imagen: " + err.message);
                    } finally { setUploadingImage(false); e.target.value = ""; }
                  }}
                />
                <span className="btn btn-ghost" style={{ height: 22, fontSize: 11, padding: "0 8px", pointerEvents: uploadingImage ? "none" : "auto" }}>
                  {uploadingImage ? "Subiendo..." : (project.structureImageUrl ? "Cambiar imagen" : "+ Subir imagen")}
                </span>
              </label>
            </div>
            {project.structureImageUrl ? (
              <div>
                <img
                  src={project.structureImageUrl}
                  alt="Estructura de la aplicación"
                  style={{ maxWidth: "100%", borderRadius: "var(--r-md)", border: "1px solid var(--border)", display: "block" }}
                />
                <button className="btn btn-ghost" style={{ height: 26, fontSize: 11, marginTop: 8, color: "var(--danger)" }}
                  onClick={async () => {
                    await onEditProject(project.id, { structure_image_url: null });
                  }}>
                  Quitar imagen
                </button>
              </div>
            ) : (
              <div style={{ fontSize: 13, color: "var(--fg-subtle)", fontStyle: "italic" }}>Sin imagen. Podés subir un diagrama, captura de pantalla o esquema de arquitectura.</div>
            )}
          </div>
        </PDCard>

        {/* ── SECCION 8: REGISTRO DE HORAS ─────────────────────── */}
        {project.workHours && project.workHours.length > 0 && (
          <PDCard>
            <PDSectionTitle>Registro de Horas ({project.workHours.length} entradas · {project.actualHours}h total)</PDSectionTitle>
            <div style={{ display: "flex", flexDirection: "column" }}>
              {project.workHours.slice().sort((a, b) => b.date > a.date ? 1 : -1).map((wh, i) => (
                <div key={wh.id || i} style={{ display: "flex", alignItems: "baseline", gap: 14, fontSize: 13, padding: "9px 0", borderBottom: i < project.workHours.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <span className="mono" style={{ color: "var(--fg-subtle)", fontSize: 12, minWidth: 80 }}>{wh.date}</span>
                  <span className="mono" style={{ fontWeight: 700, color: "var(--accent)", minWidth: 42, fontSize: 15 }}>{wh.hours}h</span>
                  <span style={{ color: "var(--fg-muted)", flex: 1 }}>{wh.desc || <em style={{ color: "var(--fg-subtle)" }}>Sin descripcion</em>}</span>
                </div>
              ))}
            </div>
          </PDCard>
        )}

        {/* ── SECCION 9: PRESUPUESTO Y FACTURACIÓN ──────────────── */}
        <PDCard>
          <div style={{ display: "flex", alignItems: "center", marginBottom: 16 }}>
            <PDSectionTitle>Presupuesto y Facturación</PDSectionTitle>
            <button className="btn btn-ghost" style={{ height: 24, fontSize: 11, padding: "0 10px", marginLeft: "auto" }}
              onClick={() => { setEditBilling(v => !v); setBillingTarifa(String(project.tarifaHora || "")); setBillingPresup(String(project.presupuesto || "")); }}>
              {editBilling ? "Cancelar" : (project.tarifaHora || project.presupuesto ? "Editar" : "+ Configurar")}
            </button>
          </div>
          {editBilling && (
            <form style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap", alignItems: "flex-end" }}
              onSubmit={async e => {
                e.preventDefault();
                setSavingBilling(true);
                try {
                  await onEditProject(project.id, {
                    tarifa_hora: billingTarifa ? parseFloat(billingTarifa) : null,
                    presupuesto: billingPresup ? parseFloat(billingPresup) : null,
                  });
                  setEditBilling(false);
                } finally { setSavingBilling(false); }
              }}>
              <div>
                <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 4 }}>Tarifa/hora ($)</div>
                <input type="number" step="0.01" min="0" value={billingTarifa} onChange={e => setBillingTarifa(e.target.value)} placeholder="0.00" style={{ ...inStyle, width: 120 }} />
              </div>
              <div>
                <div style={{ fontSize: 11, color: "var(--fg-subtle)", marginBottom: 4 }}>Presupuesto total ($)</div>
                <input type="number" step="0.01" min="0" value={billingPresup} onChange={e => setBillingPresup(e.target.value)} placeholder="0.00" style={{ ...inStyle, width: 140 }} />
              </div>
              <button type="submit" className="btn btn-primary" style={{ height: 34, fontSize: 13 }} disabled={savingBilling}>{savingBilling ? "..." : "Guardar"}</button>
            </form>
          )}
          {(project.tarifaHora || project.presupuesto) ? (() => {
            const costoReal = (project.tarifaHora || 0) * project.actualHours;
            const restante = (project.presupuesto || 0) - costoReal;
            const pctPresup = project.presupuesto > 0 ? (costoReal / project.presupuesto) * 100 : null;
            return (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 20 }}>
                {project.tarifaHora && <PDMetric label="Tarifa/hora" value={`$${project.tarifaHora}`} />}
                {project.presupuesto && <PDMetric label="Presupuesto" value={`$${project.presupuesto.toFixed(2)}`} />}
                {project.tarifaHora && <PDMetric label="Costo real" value={`$${costoReal.toFixed(2)}`} sub={`${project.actualHours}h × $${project.tarifaHora}`} color={pctPresup > 100 ? "var(--danger)" : "var(--success)"} large />}
                {project.presupuesto && project.tarifaHora && (
                  <PDMetric label={restante >= 0 ? "Restante" : "Exceso"} value={`$${Math.abs(restante).toFixed(2)}`}
                    sub={pctPresup !== null ? `${pctPresup.toFixed(0)}% del presupuesto` : ""}
                    color={restante >= 0 ? "var(--success)" : "var(--danger)"} />
                )}
              </div>
            );
          })() : (
            <div style={{ fontSize: 13, color: "var(--fg-subtle)", fontStyle: "italic" }}>Sin configuración de presupuesto. Hacé click en "+ Configurar" para agregar tarifa/hora y presupuesto.</div>
          )}
        </PDCard>

        {/* Bottom spacer */}
        <div style={{ height: 40 }} />
      </div>
    </div>
  );
}

window.MAESTRO_DETAIL = { ProjectDetail };
