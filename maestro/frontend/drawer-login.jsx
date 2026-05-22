// =====================================================================
// MAESTRO — Project detail drawer + Login screen
// =====================================================================
const { useState: useState_dl, useEffect: useEffect_dl } = React;
const D_dl = window.MAESTRO_DATA;
const I_dl = window.MAESTRO_ICONS;
const _cfg_dl = window.MAESTRO_CONFIG || {};
const API_BASE_DL = _cfg_dl.API_BASE || "http://localhost:8000";

function EditProjectForm({ project, onSave, onCancel }) {
  const [desc, setDesc] = useState_dl(project.description || "");
  const [priority, setPriority] = useState_dl(project.priority || "media");
  const [hours, setHours] = useState_dl(project.estimatedHours ? String(project.estimatedHours) : "");
  const [deadline, setDeadline] = useState_dl(project.deadline || "");
  const [fechaInicio, setFechaInicio] = useState_dl(project.fechaInicio || "");
  const [responsable, setResponsable] = useState_dl(project.responsable || "");
  const [specsText, setSpecsText] = useState_dl(project.specsText || "");
  const [saving, setSaving] = useState_dl(false);
  const inputStyle = { width: "100%", boxSizing: "border-box", padding: "7px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 13 };
  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave({
        descripcion: desc || undefined,
        prioridad: priority,
        estimated_hours: hours ? parseFloat(hours) : undefined,
        deadline: deadline || undefined,
        fecha_inicio: fechaInicio || undefined,
        responsable: responsable || undefined,
        specs_text: specsText || undefined,
      });
    } finally { setSaving(false); }
  };
  return (
    <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 10, padding: "14px 0" }}>
      <div>
        <label style={{ fontSize: 11, color: "var(--fg-muted)", display: "block", marginBottom: 3 }}>Descripción</label>
        <input value={desc} onChange={e => setDesc(e.target.value)} style={inputStyle} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <div>
          <label style={{ fontSize: 11, color: "var(--fg-muted)", display: "block", marginBottom: 3 }}>Prioridad</label>
          <select value={priority} onChange={e => setPriority(e.target.value)} style={inputStyle}>
            <option value="baja">Baja</option>
            <option value="media">Media</option>
            <option value="alta">Alta</option>
            <option value="critica">Crítica</option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: 11, color: "var(--fg-muted)", display: "block", marginBottom: 3 }}>Horas estimadas</label>
          <input type="number" min="0" step="0.5" value={hours} onChange={e => setHours(e.target.value)} style={inputStyle} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: "var(--fg-muted)", display: "block", marginBottom: 3 }}>Fecha de inicio</label>
          <input type="date" value={fechaInicio} onChange={e => setFechaInicio(e.target.value)} style={inputStyle} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: "var(--fg-muted)", display: "block", marginBottom: 3 }}>Deadline</label>
          <input type="date" value={deadline} onChange={e => setDeadline(e.target.value)} style={inputStyle} />
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 2 }}>
        <div>
          <label style={{ fontSize: 11, color: "var(--fg-muted)", display: "block", marginBottom: 3 }}>Responsable</label>
          <input value={responsable} onChange={e => setResponsable(e.target.value)} placeholder="Alexis" style={inputStyle} />
        </div>
        <div style={{ gridColumn: "1 / -1" }}>
          <label style={{ fontSize: 11, color: "var(--fg-muted)", display: "block", marginBottom: 3 }}>Especificaciones técnicas</label>
          <textarea value={specsText} onChange={e => setSpecsText(e.target.value)} placeholder="Stack, decisiones de arquitectura, notas técnicas…" style={{ ...inputStyle, height: 80, resize: "vertical" }} />
        </div>
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
        <button type="submit" className="btn btn-primary" style={{ height: 32, fontSize: 12 }} disabled={saving}>
          {saving ? "Guardando…" : "Guardar cambios"}
        </button>
        <button type="button" className="btn btn-ghost" style={{ height: 32, fontSize: 12 }} onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

const NOTE_TYPE_COLOR = { learning: "var(--accent)", decision: "var(--warning)", reflection: "var(--success)", otro: "var(--fg-subtle)" };
const NOTE_TYPE_ICON = { learning: "💡", decision: "🎯", reflection: "🔍", otro: "📝" };

function Drawer({ project, onClose, onToggleTask, onResolveBlocker, onChangeState, onEditProject, onDeleteProject, onAddHours, onAddNote, onOpenDetail, onArchiveProject, onDuplicateProject }) {
  const [editMode, setEditMode] = useState_dl(false);
  const [deleteConfirm, setDeleteConfirm] = useState_dl(false);
  const [showHoursForm, setShowHoursForm] = useState_dl(false);
  const [showNoteForm, setShowNoteForm] = useState_dl(false);
  const [hoursVal, setHoursVal] = useState_dl("");
  const [hoursDesc, setHoursDesc] = useState_dl("");
  const [noteText, setNoteText] = useState_dl("");
  const [noteType, setNoteType] = useState_dl("otro");
  const [savingHours, setSavingHours] = useState_dl(false);
  const [savingNote, setSavingNote] = useState_dl(false);
  useEffect_dl(() => {
    const onEsc = e => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [onClose]);

  if (!project) return null;
  const ratio = project.actualHours / project.estimatedHours;
  const stateClass = ratio > 1.3 ? "over" : ratio < 0.9 ? "ok" : "";

  const submitHours = async (e) => {
    e.preventDefault();
    if (!hoursVal || parseFloat(hoursVal) <= 0) return;
    setSavingHours(true);
    try {
      await onAddHours(project.id, parseFloat(hoursVal), hoursDesc);
      setHoursVal(""); setHoursDesc(""); setShowHoursForm(false);
    } finally { setSavingHours(false); }
  };

  const submitNote = async (e) => {
    e.preventDefault();
    if (!noteText.trim()) return;
    setSavingNote(true);
    try {
      await onAddNote(project.id, noteText.trim(), noteType);
      setNoteText(""); setNoteType("otro"); setShowNoteForm(false);
    } finally { setSavingNote(false); }
  };

  const handleDelete = async () => {
    await onDeleteProject(project.id);
    onClose();
  };

  const inStyle = { padding: "7px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 13 };

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer">
        <div className="drawer-head">
          <div style={{ display: "flex", flexDirection: "column", gap: 6, flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {project.blocked && <span className="pcard-blocker" />}
              <h2 className="h-display" style={{ fontSize: 22, margin: 0 }}>{project.name}</h2>
              <span className={`pcard-priority priority-${project.priority}`}>{project.priority}</span>
              <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
                <button className="btn btn-ghost" style={{ height: 28, fontSize: 11, padding: "0 10px" }}
                  onClick={() => { setEditMode(e => !e); setDeleteConfirm(false); }}>
                  {editMode ? "Cerrar" : "Editar"}
                </button>
                {!deleteConfirm ? (
                  <button className="btn btn-ghost" style={{ height: 28, fontSize: 11, padding: "0 10px", color: "var(--danger)" }}
                    onClick={() => setDeleteConfirm(true)}>
                    Eliminar
                  </button>
                ) : (
                  <>
                    <button className="btn btn-ghost" style={{ height: 28, fontSize: 11, padding: "0 10px", background: "var(--danger)", color: "#fff" }}
                      onClick={handleDelete}>
                      Confirmar
                    </button>
                    <button className="btn btn-ghost" style={{ height: 28, fontSize: 11 }}
                      onClick={() => setDeleteConfirm(false)}>
                      No
                    </button>
                  </>
                )}
              </div>
            </div>
            {!editMode && <p style={{ margin: 0, color: "var(--fg-muted)", fontSize: 13 }}>{project.description}</p>}
            {!editMode && (
              <div style={{ display: "flex", gap: 6, marginTop: 4, flexWrap: "wrap" }}>
                <span className="chip">
                  <span className="chip-dot" style={{ color: "var(--accent)" }} />
                  {D_dl.STATE_LABEL[project.state]}
                </span>
                {project.deadline && <span className="chip mono">Deadline: {project.deadline}</span>}
                <span className="chip mono">{project.daysInState}d en estado</span>
                {project.tags.map(t => <span key={t} className="chip">{t}</span>)}
              </div>
            )}
          </div>
          <button className="drawer-close" onClick={onClose}>{I_dl.x(16)}</button>
        </div>

        <div className="drawer-body">

          <div style={{ display: "contents" }}>

          {/* Edit form */}
          {editMode && (
            <section style={{ borderBottom: "1px solid var(--border)", marginBottom: 16 }}>
              <h3 className="drawer-section-title">Editar proyecto</h3>
              <EditProjectForm
                project={project}
                onSave={async (updates) => { await onEditProject(project.id, updates); setEditMode(false); }}
                onCancel={() => setEditMode(false)}
              />
            </section>
          )}

          {/* Stats */}
          <section>
            <h3 className="drawer-section-title">Estado</h3>
            <div className="drawer-stats">
              <div className="dstat">
                <div className="dstat-label">Horas trabajadas</div>
                <div className={`dstat-val ${stateClass}`}>
                  <span className="mono">{project.actualHours}h</span>
                  <span style={{ color: "var(--fg-subtle)", fontWeight: 400, fontSize: 13 }}> / {project.estimatedHours}h</span>
                </div>
              </div>
              <div className="dstat">
                <div className="dstat-label">% del estimado</div>
                <div className={`dstat-val ${stateClass}`}><span className="mono">{Math.round(ratio * 100)}%</span></div>
              </div>
              <div className="dstat">
                <div className="dstat-label">Velocity</div>
                <div className="dstat-val"><span className="mono">{project.velocity || 0}</span><span style={{ fontWeight: 400, fontSize: 12, color: "var(--fg-subtle)" }}> h/día</span></div>
              </div>
            </div>
            <div style={{ marginTop: 12 }}>
              <div className="pcard-bar">
                <div className={`pcard-bar-fill ${ratio > 1.3 ? "over" : ratio > 1 ? "warn" : ""}`}
                  style={{ width: `${Math.min(ratio * 100, 100)}%` }} />
              </div>
              {ratio > 1.3 && (
                <div style={{ marginTop: 8, fontSize: 12, color: "var(--danger)", display: "flex", alignItems: "center", gap: 6 }}>
                  {I_dl.alert(13)} +{Math.round((ratio - 1) * 100)}% por encima del estimado
                </div>
              )}
            </div>
          </section>

          {/* Quick actions */}
          <section>
            <h3 className="drawer-section-title">Acciones rápidas</h3>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
              {D_dl.STATES.map(s => s !== project.state && (
                <button key={s} className="btn btn-ghost" style={{ height: 32, fontSize: 12, padding: "0 12px" }}
                  onClick={() => onChangeState(project.id, s)}>
                  → {D_dl.STATE_LABEL_SHORT[s]}
                </button>
              ))}
            </div>

            {/* Archive / Duplicate */}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
              {onDuplicateProject && (
                <button className="btn btn-ghost" style={{ height: 30, fontSize: 12 }}
                  onClick={() => { onDuplicateProject(project.id); onClose(); }}>
                  Duplicar
                </button>
              )}
              {onArchiveProject && (
                <button className="btn btn-ghost" style={{ height: 30, fontSize: 12, color: project.archived ? "var(--accent)" : "var(--fg-muted)" }}
                  onClick={() => onArchiveProject(project.id, project.archived)}>
                  {project.archived ? "Desarchivar" : "Archivar"}
                </button>
              )}
            </div>

            {/* Inline hours form */}
            {!showHoursForm ? (
              <button className="btn btn-ghost" style={{ height: 30, fontSize: 12, marginRight: 8 }}
                onClick={() => setShowHoursForm(true)}>
                + Registrar horas
              </button>
            ) : (
              <form onSubmit={submitHours} style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 4, flexWrap: "wrap" }}>
                <input type="number" step="0.5" min="0.5" placeholder="2.5" value={hoursVal}
                  onChange={e => setHoursVal(e.target.value)}
                  style={{ ...inStyle, width: 80 }} autoFocus />
                <input placeholder="¿Qué hiciste? (opcional)" value={hoursDesc}
                  onChange={e => setHoursDesc(e.target.value)}
                  style={{ ...inStyle, flex: 1, minWidth: 140 }} />
                <button type="submit" className="btn btn-primary" style={{ height: 32, fontSize: 12 }} disabled={savingHours}>
                  {savingHours ? "…" : "Guardar"}
                </button>
                <button type="button" className="btn btn-ghost" style={{ height: 32, fontSize: 12 }}
                  onClick={() => setShowHoursForm(false)}>
                  {I_dl.x(12)}
                </button>
              </form>
            )}

            {/* Inline note form */}
            {!showNoteForm ? (
              <button className="btn btn-ghost" style={{ height: 30, fontSize: 12 }}
                onClick={() => setShowNoteForm(true)}>
                + Agregar nota
              </button>
            ) : (
              <form onSubmit={submitNote} style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8, flexWrap: "wrap" }}>
                <input placeholder="Nota o aprendizaje…" value={noteText}
                  onChange={e => setNoteText(e.target.value)}
                  style={{ ...inStyle, flex: 1, minWidth: 160 }} autoFocus />
                <select value={noteType} onChange={e => setNoteType(e.target.value)} style={{ ...inStyle, width: 110 }}>
                  <option value="otro">Otro</option>
                  <option value="learning">Learning</option>
                  <option value="decision">Decisión</option>
                  <option value="reflection">Reflexión</option>
                </select>
                <button type="submit" className="btn btn-primary" style={{ height: 32, fontSize: 12 }} disabled={savingNote}>
                  {savingNote ? "…" : "Guardar"}
                </button>
                <button type="button" className="btn btn-ghost" style={{ height: 32, fontSize: 12 }}
                  onClick={() => setShowNoteForm(false)}>
                  {I_dl.x(12)}
                </button>
              </form>
            )}
          </section>

          {/* Blockers */}
          {project.blockers.length > 0 && (
            <section>
              <h3 className="drawer-section-title">Bloqueadores</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {project.blockers.map(b => (
                  <div key={b.id} className={`blocker-row ${b.resolved ? "resolved" : ""}`}>
                    <div className="blocker-icon">{b.resolved ? I_dl.check(12) : I_dl.blocked(12)}</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 500 }}>{b.desc}</div>
                      <div className="task-meta">
                        Tipo: {b.type} · {b.days} días
                      </div>
                    </div>
                    {!b.resolved && (
                      <button className="btn btn-ghost" style={{ height: 28, fontSize: 11, padding: "0 10px" }}
                        onClick={() => onResolveBlocker(project.id, b.id)}>
                        Resolver
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Tasks */}
          <section>
            <h3 className="drawer-section-title">Tareas ({project.tasks.filter(t => t.done).length}/{project.tasks.length})</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {project.tasks.map(t => (
                <div key={t.id} className="task-row">
                  <div className={`task-check ${t.done ? "done" : ""}`}
                    onClick={() => onToggleTask(project.id, t.id)}>
                    {t.done && I_dl.check(12)}
                  </div>
                  <div className="task-body">
                    <div className={`task-name ${t.done ? "done" : ""}`}>{t.name}</div>
                    <div className="task-meta" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <span>{t.hours > 0 ? `${t.hours}h trabajadas` : "no iniciada"}{t.estimated ? ` · ${t.estimated}h est.` : ""}</span>
                      {t.fechaInicio && <span style={{ color: "var(--accent)" }}>▶ {t.fechaInicio}</span>}
                      {t.fechaVencimiento && <span style={{ color: new Date(t.fechaVencimiento) < new Date() && !t.done ? "var(--danger)" : "var(--warning)" }}>⏱ {t.fechaVencimiento}</span>}
                    </div>
                  </div>
                </div>
              ))}
              {project.tasks.length === 0 && (
                <div style={{ fontSize: 12, color: "var(--fg-subtle)", padding: 14, textAlign: "center", border: "1px dashed var(--border)", borderRadius: "var(--r-md)" }}>
                  Sin tareas — pedile al asistente o usá "Nueva tarea"
                </div>
              )}
            </div>
          </section>

          {/* Notes */}
          <section>
            <h3 className="drawer-section-title">Notas & Learnings</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {project.notes.map(n => (
                <div key={n.id} className="note-row">
                  <div style={{ flex: 1 }}>
                    <div style={{ fontStyle: "italic" }}>"{n.text}"</div>
                    <div className="task-meta">{n.type} · {n.date}</div>
                  </div>
                </div>
              ))}
              {project.notes.length === 0 && (
                <div style={{ fontSize: 12, color: "var(--fg-subtle)", fontStyle: "italic" }}>Sin notas todavía</div>
              )}
            </div>
          </section>

          {/* Timeline — enriched with state changes + hours */}
          <section>
            <h3 className="drawer-section-title">Timeline</h3>
            <div className="timeline-history">
              {project.history.length === 0 && (
                <div style={{ fontSize: 12, color: "var(--fg-subtle)", padding: "8px 0" }}>Sin actividad registrada</div>
              )}
              {project.history.map((h, i) => (
                <div key={i} className="history-row">
                  <div className="history-time">{h.time}</div>
                  <div className="history-axis">
                    <div className={`history-dot ${h.type === "blocker" ? "blocker" : h.type === "task" ? "task" : h.type === "note" ? "note" : h.type === "state" ? "state" : ""}`} />
                  </div>
                  <div className="history-text">
                    {h.text}
                    <div className="history-meta">{h.type}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Links */}
          {project.links && project.links.length > 0 && (
            <section>
              <h3 className="drawer-section-title">Enlaces</h3>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {project.links.map(l => (
                  <a key={l.label} href={l.url} className="chip" style={{ height: 28, padding: "0 10px", cursor: "pointer", textDecoration: "none" }}>
                    {I_dl.link(12)} {l.label}
                  </a>
                ))}
              </div>
            </section>
          )}

          {/* Carpeta completa */}
          {onOpenDetail && (
            <section style={{ paddingTop: 8 }}>
              <button
                className="btn btn-primary"
                style={{ width: "100%", height: 36, fontSize: 13, display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}
                onClick={() => onOpenDetail(project.id)}
              >
                Abrir carpeta completa →
              </button>
            </section>
          )}

          </div>{/* end display:contents */}
        </div>{/* end drawer-body */}
      </aside>
    </>
  );
}

// ============== Login Screen ==============
function Login({ onLogin }) {
  const [user, setUser] = useState_dl("");
  const [pw, setPw] = useState_dl("");
  const [showPw, setShowPw] = useState_dl(false);
  const [remember, setRemember] = useState_dl(true);
  const [err, setErr] = useState_dl({});
  const [loading, setLoading] = useState_dl(false);
  const [lockoutUntil, setLockoutUntil] = useState_dl(null);
  const [chatIdx, setChatIdx] = useState_dl(0);

  const chatExamples = [
    { user: "agregá 3h a APODERAR", agent: "Listo ✓ 21h totales · +163% del estimado", warn: true },
    { user: "¿cuáles están en riesgo?", agent: "Encontré 2: FOLIAR 🔴 bloqueado · ARCA Bot +46%" },
    { user: "pasá ARCA Bot a listo", agent: "Confirmá: testing → listo · 5d en testing" },
    { user: "se resolvió el bloqueador de FOLIAR", agent: "Buenísimo ✓ desbloqueado · 4d perdidos" },
  ];

  useEffect_dl(() => {
    const id = setInterval(() => setChatIdx(i => (i + 1) % chatExamples.length), 4200);
    return () => clearInterval(id);
  }, []);

  const submit = async e => {
    e.preventDefault();
    if (lockoutUntil && Date.now() < lockoutUntil) return;
    const errs = {};
    if (!user.trim()) errs.user = "Ingresá tu usuario";
    if (!pw) errs.pw = "Ingresá tu contraseña";
    if (pw.length > 0 && pw.length < 8) errs.pw = "Mínimo 8 caracteres";
    if (Object.keys(errs).length) { setErr(errs); return; }
    setErr({});
    setLoading(true);
    try {
      const res = await fetch(API_BASE_DL + "/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: user.trim(), password: pw }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.status === 429) {
        const retryAfter = parseInt(res.headers.get("Retry-After") || "900");
        setLockoutUntil(Date.now() + retryAfter * 1000);
        setErr({ general: data.detail || `Demasiados intentos. Esperá ${Math.ceil(retryAfter / 60)} minutos.` });
        return;
      }
      if (!res.ok) {
        setErr({ general: data.detail || "Usuario o contraseña incorrectos" });
        return;
      }
      setLockoutUntil(null);
      D_dl.setToken(data.access_token);
      onLogin({ username: data.username, displayName: data.display_name });
    } catch (e) {
      setErr({ general: "No se pudo conectar al servidor. Verificá que el backend esté activo." });
    } finally {
      setLoading(false);
    }
  };

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Buen día" : hour < 19 ? "Buenas tardes" : "Buenas noches";
  const current = chatExamples[chatIdx];

  return (
    <div className="login">
      {/* ========= Left: hero stage ========= */}
      <div className="login-stage">
        <div className="login-orb o1" />
        <div className="login-orb o2" />
        <div className="login-orb o3" />

        <div className="stage-head">
          <div className="stage-brand">
            <div className="brand-mark">M</div>
            <span>MAESTRO</span>
            <span className="brand-tag">v0.1 · BETA</span>
          </div>
          <div className="stage-status">
            <span className="stage-status-dot" />
            Todos los sistemas operativos
          </div>
        </div>

        {/* Floating preview cards */}
        <div className="stage-demo d1">
          <div className="demo-kpi">
            <div className="demo-kpi-label">Horas hoy</div>
            <div className="demo-kpi-val">4.5<small>h</small></div>
            <div className="demo-kpi-delta">↑ +0.5h vs ayer</div>
          </div>
        </div>
        <div className="stage-demo d2">
          <div className="demo-card">
            <div className="demo-card-name">FOLIAR</div>
            <div className="demo-card-bar"><div /></div>
            <div className="demo-card-meta">
              <span>7h / 12h</span>
              <span>bloqueado 4d</span>
            </div>
          </div>
        </div>
        <div className="stage-demo d3">
          <div className="demo-chat">
            <div className="demo-chat-av">M</div>
            <div className="demo-chat-body">
              <div key={"u-" + chatIdx} style={{ color: "oklch(1 0 0 / 0.65)", fontSize: 11.5, marginBottom: 4, animation: "fadeIn 360ms ease-out" }}>
                tú: "{current.user}"
              </div>
              <div key={"a-" + chatIdx} style={{ color: current.warn ? "oklch(0.85 0.15 70)" : "oklch(0.92 0.04 240)", animation: "fadeIn 600ms ease-out 100ms backwards" }}>
                {current.agent}
              </div>
            </div>
          </div>
        </div>

        <div className="stage-core">
          <div className="stage-eyebrow">
            {I_dl.sparkles(11)} Project manager + IA
          </div>
          <h1 className="stage-title">
            Tu panorama,<br />
            en <em>lenguaje natural</em>.
          </h1>
          <p className="stage-sub">
            Decile «agregá 3 horas a APODERAR» o «¿cuáles están en riesgo?».
            El asistente entiende, ejecuta y te trae el análisis.
          </p>

          <div className="stage-features">
            <div className="stage-feature">
              <div className="stage-feature-icon">{I_dl.folder(15)}</div>
              <div className="stage-feature-text">
                <strong>Dashboard en vivo</strong>
                <span>Estado de cada proyecto</span>
              </div>
            </div>
            <div className="stage-feature">
              <div className="stage-feature-icon">{I_dl.sparkles(15)}</div>
              <div className="stage-feature-text">
                <strong>Asistente conversacional</strong>
                <span>Acciones por chat</span>
              </div>
            </div>
            <div className="stage-feature">
              <div className="stage-feature-icon">{I_dl.alert(15)}</div>
              <div className="stage-feature-text">
                <strong>Alertas inteligentes</strong>
                <span>Detecta riesgos solo</span>
              </div>
            </div>
            <div className="stage-feature">
              <div className="stage-feature-icon">{I_dl.trend(15)}</div>
              <div className="stage-feature-text">
                <strong>Insights de velocity</strong>
                <span>Aprende de tus tiempos</span>
              </div>
            </div>
          </div>
        </div>

        <div className="stage-foot">
          <div className="stage-stats">
            <div>
              <div className="stage-stat-val">7</div>
              <div className="stage-stat-lbl">Proyectos</div>
            </div>
            <div>
              <div className="stage-stat-val">82h</div>
              <div className="stage-stat-lbl">Trackeadas</div>
            </div>
            <div>
              <div className="stage-stat-val">1.2k</div>
              <div className="stage-stat-lbl">Msgs IA</div>
            </div>
          </div>
          <div className="stage-quote">
            «Pasé de buscar 20 min dónde estaba parado a saberlo en 5 segundos.»
            <div className="stage-quote-att">— Alexis · Estudio Arrechea</div>
          </div>
        </div>
      </div>

      {/* ========= Right: form ========= */}
      <div className="login-formside">
        <div className="formside-top">
          <div></div>
          <a href="#" style={{ color: "var(--fg-muted)", textDecoration: "none" }}>
            ¿Sos nuevo? <span style={{ color: "var(--accent)", fontWeight: 500 }}>Pedir acceso →</span>
          </a>
        </div>

        <form className="login-card" onSubmit={submit}>
          <div className="login-greeting">
            <div className="login-eyebrow">{greeting} 👋</div>
            <h1>Entrá a tu panel</h1>
            <p>Tu sesión anterior cerró hace 2 horas.</p>
          </div>

          <div className="field">
            <label className="field-label">Usuario</label>
            <div className="field-shell">
              <input
                className="field-input"
                value={user}
                onChange={e => { setUser(e.target.value); setErr(s => ({ ...s, user: null, general: null })); }}
                placeholder="alexis"
                autoComplete="username"
              />
              <span className="field-icon">{I_dl.user(15)}</span>
            </div>
            {err.user && <div className="field-error">{I_dl.alert(12)} {err.user}</div>}
          </div>

          <div className="field">
            <label className="field-label">Contraseña</label>
            <div className="field-shell">
              <input
                type={showPw ? "text" : "password"}
                className="field-input"
                value={pw}
                onChange={e => { setPw(e.target.value); setErr(s => ({ ...s, pw: null, general: null })); }}
                placeholder="••••••••"
                autoComplete="current-password"
              />
              <span className="field-icon">{I_dl.lock(15)}</span>
              <button type="button" className="password-eye" onClick={() => setShowPw(s => !s)} title={showPw ? "Ocultar" : "Mostrar"}>
                {showPw
                  ? <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" /><line x1="1" y1="1" x2="23" y2="23" /></svg>
                  : <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></svg>}
              </button>
            </div>
            {err.pw && <div className="field-error">{I_dl.alert(12)} {err.pw}</div>}
          </div>

          <div className="field-aux">
            <label>
              <input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} />
              <span className="ck">{remember && I_dl.check(11)}</span>
              Recordarme 30 días
            </label>
            <a href="#" onClick={e => e.preventDefault()}>¿Olvidaste tu contraseña?</a>
          </div>

          {err.general && (
            <div className="field-error" style={{ marginBottom: 12, padding: "10px 12px", background: "var(--danger-soft)", border: "1px solid var(--danger)", borderRadius: 10 }}>
              {I_dl.alert(12)} {err.general}
            </div>
          )}

          {lockoutUntil && Date.now() < lockoutUntil && (
            <div style={{ padding: "8px 12px", borderRadius: "var(--r-md)", background: "var(--danger-soft)", border: "1px solid var(--danger)", fontSize: 12, color: "var(--danger)", marginBottom: 8 }}>
              Acceso temporalmente bloqueado. Demasiados intentos fallidos.
            </div>
          )}
          <button type="submit" className="btn btn-primary login-btn"
            disabled={loading || (lockoutUntil && Date.now() < lockoutUntil)}>
            {loading ? (
              <div className="typing-dots"><span style={{ background: "#fff" }} /><span style={{ background: "#fff" }} /><span style={{ background: "#fff" }} /></div>
            ) : (
              <>Entrar al panel {I_dl.arrowRight(14)}</>
            )}
          </button>

          <div className="login-divider"><span>o continuá con</span></div>

          <div className="sso-row">
            <button type="button" className="sso-btn">
              <svg width="16" height="16" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z" /><path fill="#FF3D00" d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z" /><path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238C29.211 35.091 26.715 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z" /><path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303c-.792 2.237-2.231 4.166-4.087 5.571.001-.001.002-.001.003-.002l6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z" /></svg>
              Google
            </button>
            <button type="button" className="sso-btn">
              <svg width="14" height="14" viewBox="0 0 24 24"><rect width="10" height="10" fill="#F25022" /><rect x="12" width="10" height="10" fill="#7FBA00" /><rect y="12" width="10" height="10" fill="#00A4EF" /><rect x="12" y="12" width="10" height="10" fill="#FFB900" /></svg>
              Microsoft
            </button>
          </div>

          <div className="login-cred">
            <div className="cred-eyebrow">Credenciales de acceso</div>
            <div className="cred-row" style={{ color: "var(--fg-muted)", fontSize: 12 }}>
              Contactá al administrador del sistema si no tenés acceso.
            </div>
          </div>
        </form>

        <div className="formside-bot">
          <span className="formside-status">
            <span className="formside-status-dot" />
            Supabase · Claude API · OK
          </span>
          <span>
            <a href="#">Privacidad</a> · <a href="#">Términos</a> · <a href="#">v0.1.0</a>
          </span>
        </div>
      </div>
    </div>
  );
}

window.MAESTRO_DL = { Drawer, Login };
