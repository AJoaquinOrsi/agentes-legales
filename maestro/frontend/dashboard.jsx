// =====================================================================
// MAESTRO — Header + Home + Projects section
// =====================================================================
const { useState, useEffect, useMemo, useRef, useCallback } = React;
const D = window.MAESTRO_DATA;
const I = window.MAESTRO_ICONS;

const NAV = [
  { id: "inicio", label: "Inicio", icon: () => I.spark(14) },
  { id: "proyectos", label: "Proyectos", icon: () => I.folder(14) },
  { id: "tareas", label: "Tareas", icon: () => I.task(14) },
  { id: "calendario", label: "Calendario", icon: () => I.clock(14) },
  { id: "stats", label: "Estadísticas", icon: () => I.trend(14) },
  { id: "asistente", label: "Asistente", icon: () => I.sparkles(14) },
  { id: "config", label: "Config", icon: () => I.cog(14) },
];

// ── Notification Bell ─────────────────────────────────────────────────────────
const NOTIF_COLORS = {
  tarea_vencida: "var(--danger)",
  tarea_proxima: "var(--warning)",
  proyecto_bloqueado: "#f97316",
  sistema: "var(--accent)",
};
const NOTIF_ICONS = {
  tarea_vencida: "🔴",
  tarea_proxima: "🟡",
  proyecto_bloqueado: "🚧",
  sistema: "ℹ️",
};

function NotificationBell({ onOpenProject }) {
  const [open, setOpen] = useState(false);
  const [notifs, setNotifs] = useState([]);
  const [unread, setUnread] = useState(0);
  const ref = useRef(null);

  const load = async () => {
    try {
      const data = await D.API.getNotifications();
      setNotifs(data || []);
      setUnread((data || []).filter(n => !n.leida).length);
    } catch(e) {}
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 60000); // poll cada 60s
    return () => clearInterval(interval);
  }, []);

  // Cerrar al hacer click afuera
  useEffect(() => {
    const handler = e => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const markRead = async (id) => {
    await D.API.markNotificationRead(id);
    setNotifs(prev => prev.map(n => n.id === id ? { ...n, leida: true } : n));
    setUnread(prev => Math.max(0, prev - 1));
  };

  const markAll = async () => {
    await D.API.markAllNotificationsRead();
    setNotifs(prev => prev.map(n => ({ ...n, leida: true })));
    setUnread(0);
  };

  const remove = async (e, id) => {
    e.stopPropagation();
    await D.API.deleteNotification(id);
    const removed = notifs.find(n => n.id === id);
    setNotifs(prev => prev.filter(n => n.id !== id));
    if (removed && !removed.leida) setUnread(prev => Math.max(0, prev - 1));
  };

  const handleClick = async (n) => {
    if (!n.leida) await markRead(n.id);
    if (n.project_id && onOpenProject) { onOpenProject(n.project_id); setOpen(false); }
  };

  const timeAgo = (dt) => {
    const mins = Math.floor((Date.now() - new Date(dt)) / 60000);
    if (mins < 1) return "ahora";
    if (mins < 60) return `${mins}m`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h`;
    return `${Math.floor(hrs / 24)}d`;
  };

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button className="btn btn-ghost btn-icon" title="Notificaciones"
        onClick={() => { setOpen(v => !v); if (!open) load(); }}
        style={{ position: "relative" }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
        {unread > 0 && (
          <span style={{ position: "absolute", top: 2, right: 2, minWidth: 16, height: 16, borderRadius: 8, background: "var(--danger)", color: "#fff", fontSize: 10, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center", padding: "0 3px", lineHeight: 1 }}>
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div style={{ position: "absolute", top: "calc(100% + 8px)", right: 0, width: 340, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: "var(--r-lg)", boxShadow: "var(--shadow-md)", zIndex: 9999, overflow: "hidden" }}>
          {/* Header */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 14px 10px", borderBottom: "1px solid var(--border)" }}>
            <span style={{ fontSize: 13, fontWeight: 700 }}>Notificaciones {unread > 0 && <span style={{ marginLeft: 4, background: "var(--danger)", color: "#fff", borderRadius: 8, fontSize: 10, padding: "1px 5px" }}>{unread}</span>}</span>
            {unread > 0 && (
              <button className="btn btn-ghost" style={{ height: 24, fontSize: 11, padding: "0 8px" }} onClick={markAll}>
                Marcar todo leído
              </button>
            )}
          </div>

          {/* Lista */}
          <div style={{ maxHeight: 380, overflowY: "auto" }}>
            {notifs.length === 0 ? (
              <div style={{ padding: "24px 14px", textAlign: "center", fontSize: 13, color: "var(--fg-muted)" }}>
                🎉 Sin notificaciones pendientes
              </div>
            ) : notifs.map(n => (
              <div key={n.id} onClick={() => handleClick(n)}
                style={{ display: "flex", gap: 10, padding: "10px 14px", cursor: n.project_id ? "pointer" : "default", background: n.leida ? "transparent" : "color-mix(in srgb, var(--accent) 4%, transparent)", borderBottom: "1px solid var(--border)", transition: "background .1s" }}
                onMouseEnter={e => e.currentTarget.style.background = "var(--bg-subtle)"}
                onMouseLeave={e => e.currentTarget.style.background = n.leida ? "transparent" : "color-mix(in srgb, var(--accent) 4%, transparent)"}>
                <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>{NOTIF_ICONS[n.tipo] || "ℹ️"}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: n.leida ? 400 : 600, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{n.titulo}</div>
                  {n.mensaje && <div style={{ fontSize: 11, color: "var(--fg-muted)", marginTop: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{n.mensaje}</div>}
                  <div style={{ fontSize: 10, color: "var(--fg-subtle)", marginTop: 2 }}>{timeAgo(n.created_at)}</div>
                </div>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flexShrink: 0 }}>
                  {!n.leida && <div style={{ width: 7, height: 7, borderRadius: "50%", background: NOTIF_COLORS[n.tipo] || "var(--accent)" }} />}
                  <button className="btn btn-ghost" style={{ height: 18, width: 18, padding: 0, fontSize: 11, color: "var(--fg-subtle)" }}
                    onClick={e => remove(e, n.id)} title="Eliminar">×</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Header({ view, setView, theme, setTheme, onLogout, alertCount, projects = [], onOpenProject }) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIdx, setSelectedIdx] = useState(0);
  const searchRef = useRef(null);

  useEffect(() => {
    if (searchOpen && searchRef.current) searchRef.current.focus();
  }, [searchOpen]);

  useEffect(() => {
    if (!searchOpen) { setSearchQuery(""); setSelectedIdx(0); }
  }, [searchOpen]);

  useEffect(() => { setSelectedIdx(0); }, [searchQuery]);

  // Ctrl+K global shortcut
  useEffect(() => {
    const onKey = e => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") { e.preventDefault(); setSearchOpen(v => !v); }
      if (e.key === "Escape") setSearchOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const searchResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q || q.length < 2) return [];
    const results = [];
    projects.forEach(p => {
      if (p.name.toLowerCase().includes(q) || (p.description || "").toLowerCase().includes(q) || p.tags.some(t => t.toLowerCase().includes(q))) {
        results.push({ type: "proyecto", label: p.name, sub: p.description?.slice(0, 60) || "", id: p.id });
      }
      p.tasks.forEach(t => {
        if (t.name.toLowerCase().includes(q))
          results.push({ type: "tarea", label: t.name, sub: p.name, id: p.id });
      });
      (p.notes || []).forEach(n => {
        if (n.text.toLowerCase().includes(q))
          results.push({ type: "nota", label: n.text.slice(0, 60), sub: p.name, id: p.id });
      });
    });
    return results.slice(0, 10);
  }, [searchQuery, projects]);

  const handleResultClick = (r) => {
    onOpenProject(r.id);
    setSearchOpen(false);
    setSearchQuery("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setSelectedIdx(i => Math.min(i + 1, searchResults.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setSelectedIdx(i => Math.max(i - 1, 0)); }
    else if (e.key === "Enter" && searchResults[selectedIdx]) handleResultClick(searchResults[selectedIdx]);
    else if (e.key === "Escape") setSearchOpen(false);
  };

  return (
    <header className="header">
      <div className="header-left">
        <div className="brand">
          <div className="brand-mark">
            <svg viewBox="0 0 32 32" width="20" height="20" fill="none">
              <defs>
                <linearGradient id="mLogo" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#c4b5fd"/>
                  <stop offset="50%" stopColor="#a78bfa"/>
                  <stop offset="100%" stopColor="#7c3aed"/>
                </linearGradient>
              </defs>
              <path d="M4 26V6L16 18 28 6v20" stroke="rgba(196,181,253,0.25)" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M4 26V6L16 18 28 6v20" stroke="url(#mLogo)" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span>MAESTRO</span>
          <span className="brand-tag">v0.1 · BETA</span>
        </div>
        <nav className="nav-tabs">
          {NAV.map(n => (
            <button
              key={n.id}
              className={`nav-tab ${view === n.id ? "active" : ""}`}
              onClick={() => setView(n.id)}
              title={n.label}
            >
              <span className="nav-tab-dot" />
              {n.icon()}
              <span>{n.label}</span>
              {n.id === "inicio" && alertCount > 0 && (
                <span className="nav-tab-badge">{alertCount}</span>
              )}
            </button>
          ))}
        </nav>
      </div>
      <div className="header-actions">
        {/* Global search */}
        <div style={{ position: "relative" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
              <svg style={{ position: "absolute", left: 8, pointerEvents: "none", color: "var(--fg-subtle)" }} width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
              <input
                ref={searchRef}
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                onFocus={() => setSearchOpen(true)}
                placeholder="Buscar…"
                onKeyDown={handleKeyDown}
                style={{ width: searchOpen ? 220 : 130, paddingLeft: 26, paddingRight: searchOpen ? 8 : 36, paddingTop: 5, paddingBottom: 5, borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 13, outline: "none", transition: "width 0.2s" }}
              />
              {!searchOpen && (
                <kbd style={{ position: "absolute", right: 6, fontSize: 10, color: "var(--fg-subtle)", background: "var(--bg-subtle)", border: "1px solid var(--border)", borderRadius: 4, padding: "1px 4px", pointerEvents: "none" }}>⌘K</kbd>
              )}
            </div>
            {searchOpen && searchQuery && (
              <button className="btn btn-ghost btn-icon" onClick={() => { setSearchQuery(""); setSearchOpen(false); }}>{I.x(13)}</button>
            )}
          </div>
          {searchOpen && searchResults.length > 0 && (
            <div style={{ position: "absolute", top: "calc(100% + 6px)", right: 0, width: 340, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: "var(--r-md)", boxShadow: "var(--shadow-md)", zIndex: 9999, overflow: "hidden" }}>
              {searchResults.map((r, i) => {
                const typeColor = r.type === "proyecto" ? "var(--accent)" : r.type === "nota" ? "var(--warning)" : "var(--fg-muted)";
                return (
                  <div key={i} onClick={() => handleResultClick(r)}
                    style={{ padding: "9px 14px", cursor: "pointer", borderBottom: i < searchResults.length - 1 ? "1px solid var(--border)" : "none", display: "flex", gap: 10, alignItems: "center", background: i === selectedIdx ? "var(--bg-subtle)" : "transparent" }}
                    onMouseEnter={() => setSelectedIdx(i)}>
                    <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, background: `color-mix(in srgb, ${typeColor} 12%, transparent)`, color: typeColor, fontWeight: 700, whiteSpace: "nowrap", textTransform: "uppercase" }}>{r.type}</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.label}</div>
                      {r.sub && <div style={{ fontSize: 11, color: "var(--fg-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.sub}</div>}
                    </div>
                    {i === selectedIdx && <span style={{ fontSize: 10, color: "var(--fg-subtle)" }}>↵</span>}
                  </div>
                );
              })}
              <div style={{ padding: "6px 14px", fontSize: 11, color: "var(--fg-subtle)", borderTop: "1px solid var(--border)", display: "flex", gap: 12 }}>
                <span>↑↓ navegar</span><span>↵ abrir</span><span>Esc cerrar</span>
              </div>
            </div>
          )}
          {searchOpen && searchQuery.length >= 2 && searchResults.length === 0 && (
            <div style={{ position: "absolute", top: "calc(100% + 6px)", right: 0, width: 260, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: "var(--r-md)", boxShadow: "var(--shadow-md)", zIndex: 9999, padding: "12px 14px", fontSize: 13, color: "var(--fg-muted)" }}>
              Sin resultados para "{searchQuery}"
            </div>
          )}
        </div>

        <NotificationBell onOpenProject={onOpenProject} />
        <button className="btn btn-ghost btn-icon" title="Cambiar tema"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
          {theme === "dark" ? I.sun() : I.moon()}
        </button>
        <div className="user-pill">
          <span className="user-name">Alexis</span>
          <div className="user-avatar">AA</div>
        </div>
        <button className="btn btn-ghost btn-icon" title="Cerrar sesión" onClick={onLogout}>
          {I.logout()}
        </button>
      </div>
    </header>
  );
}

// -------- Sparkline --------
function Sparkline({ data, color = "var(--accent)" }) {
  const w = 70, h = 26;
  const max = Math.max(...data), min = Math.min(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * (h - 4) - 2}`).join(" ");
  const last = pts.split(" ").pop().split(",");
  return (
    <svg className="kpi-spark" width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <polyline fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" points={pts} opacity="0.85" />
      <circle cx={last[0]} cy={last[1]} r="2.2" fill={color} />
    </svg>
  );
}

function KPI({ label, icon, value, unit, delta, deltaDir, spark }) {
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
          {deltaDir === "up" ? I.trend(12) : deltaDir === "down" ? I.trendDown(12) : null}
          <span>{delta}</span>
        </div>
      )}
      {spark && <Sparkline data={spark} />}
    </div>
  );
}

// -------- Alerts banner --------
function Alerts({ projects, onOpenProject }) {
  const risks = projects.filter(p => p.blocked || p.actualHours > p.estimatedHours * 1.4 || p.daysInState > 4);
  if (risks.length === 0) return null;
  return (
    <div className="alerts">
      <div className="alerts-head">
        <div className="alerts-title">
          <span style={{ color: "var(--warning)" }}>{I.alert(16)}</span>
          Atención requerida · {risks.length} {risks.length === 1 ? "proyecto" : "proyectos"}
        </div>
        <span className="chip mono" style={{ background: "var(--bg-surface)" }}>actualizado hace 2 min</span>
      </div>
      <div className="alerts-list">
        {risks.map(p => (
          <div key={p.id} className="alert-row" onClick={() => onOpenProject(p.id)}>
            <div className={`alert-icon-wrap ${p.blocked ? "danger" : "warning"}`}>
              {p.blocked ? I.blocked(14) : I.alert(14)}
            </div>
            <div className="alert-text">
              <strong>{p.name}</strong>
              {" — "}
              {p.blocked
                ? <span>bloqueado <span className="mono">{p.blockers[0]?.days || "?"}d</span> · {p.blockers[0]?.desc}</span>
                : p.actualHours > p.estimatedHours * 1.4
                ? <span><span className="mono">{p.actualHours}h</span> vs <span className="mono">{p.estimatedHours}h</span> estimadas (+{Math.round((p.actualHours / p.estimatedHours - 1) * 100)}%)</span>
                : <span><span className="mono">{p.daysInState}</span> días en {D.STATE_LABEL_SHORT[p.state].toLowerCase()} sin movimiento</span>}
            </div>
            <span className="alert-meta">{p.lastUpdate} →</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// -------- Home section --------
function HomeSection({ projects, onOpenProject, onToggleTask, onJumpView, todayHours, tasksDone, projectsTouched }) {
  const activeCount = projects.filter(p => p.state !== "produccion").length;
  const blockedCount = projects.filter(p => p.blocked).length;
  const allTasks = projects.flatMap(p => p.tasks);
  const totalTasks = allTasks.length;
  const doneTasks = allTasks.filter(t => t.done).length;
  const avgVelocity = projects.length
    ? (projects.reduce((s, p) => s + (p.velocity || 0), 0) / projects.length).toFixed(1)
    : "—";

  // Today's tasks: pending tasks across projects, sorted (blocked projects first)
  const todayTasks = useMemo(() => {
    const all = [];
    projects.forEach(p => {
      p.tasks.filter(t => !t.done).slice(0, 3).forEach(t => {
        all.push({ ...t, project: p });
      });
    });
    all.sort((a, b) => {
      if (a.project.blocked !== b.project.blocked) return a.project.blocked ? -1 : 1;
      const pr = { alta: 0, media: 1, baja: 2 };
      return pr[a.project.priority] - pr[b.project.priority];
    });
    return all.slice(0, 6);
  }, [projects]);

  // Upcoming deadlines — deadline is ISO "YYYY-MM-DD" or null
  const MONTHS_SHORT = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];
  const upcoming = useMemo(() => {
    return projects
      .filter(p => p.deadline && p.deadline !== "—")
      .map(p => {
        const parts = p.deadline.split("-");
        const day = parts[2] ? String(parseInt(parts[2])) : p.deadline;
        const month = parts[1] ? MONTHS_SHORT[parseInt(parts[1]) - 1] || "" : "";
        return { project: p, day, month };
      })
      .slice(0, 5);
  }, [projects]);

  const isEmpty = projects.length === 0;

  return (
    <section className="section">
      <div className="section-head">
        <div>
          <div className="section-eyebrow">Inicio</div>
          <h1 className="section-title">
            {isEmpty ? "Bienvenido, Alexis" : "Buen día, Alexis"}
          </h1>
          <p className="section-subtitle">
            {new Date().toLocaleDateString("es-AR", { weekday: "long", day: "numeric", month: "long" })}
            {!isEmpty && ` · ${activeCount} proyectos activos · ${doneTasks} tareas listas hoy`}
            {isEmpty && " · todavía no hay proyectos cargados"}
          </p>
        </div>
        <div className="dash-now">
          <span>● en vivo</span>
          <span>14:30</span>
        </div>
      </div>

      <div className="summary-grid">
        <KPI label="Horas hoy" icon={I.clock(14)} value={todayHours.toFixed(1)} unit="h"
          delta={isEmpty ? "sin registros" : "+0.5h vs ayer"} deltaDir={isEmpty ? "" : "up"} />
        <KPI label="Tareas completadas" icon={I.check(14)} value={String(doneTasks)} unit={`/${totalTasks || 0}`}
          delta={totalTasks ? `${totalTasks - doneTasks} pendientes` : "sin tareas"} />
        <KPI label="Proyectos activos" icon={I.folder(14)} value={String(activeCount)}
          delta={isEmpty ? "creá tu primero" : `${blockedCount} bloqueado${blockedCount === 1 ? "" : "s"}`}
          deltaDir={blockedCount > 0 ? "down" : ""} />
        <KPI label="Velocity 7d" icon={I.bolt(14)} value={avgVelocity} unit={isEmpty ? "" : "h/día"}
          delta={isEmpty ? "sin datos" : "-12% vs semana pasada"} deltaDir={isEmpty ? "" : "down"} />
      </div>

      <Alerts projects={projects} onOpenProject={onOpenProject} />

      {isEmpty && (
        <div className="empty-hero">
          <div className="empty-hero-mark">
            {I.sparkles(28)}
          </div>
          <h2>Arrancá tu primer proyecto</h2>
          <p>
            Crealo desde el asistente con lenguaje natural, o ingresalo manualmente.<br />
            El dashboard, las tareas y las estadísticas se van llenando solas.
          </p>
          <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap", justifyContent: "center" }}>
            <button className="btn btn-primary" onClick={() => onJumpView("asistente")}>
              {I.sparkles(14)} Pedirle al asistente
            </button>
            <button className="btn btn-ghost" onClick={() => onJumpView("proyectos")}>
              {I.folder(14)} Ir a proyectos
            </button>
          </div>
          <div className="empty-hero-hints">
            <span className="empty-hint-chip">«creá un proyecto APODERAR»</span>
            <span className="empty-hint-chip">«agregá una tarea de testing»</span>
            <span className="empty-hint-chip">«¿qué puedo hacer acá?»</span>
          </div>
        </div>
      )}

      {!isEmpty && (
        <div className="home-grid">
          <div className="card">
            <h3 className="card-title">
              Tareas para hoy
              <button className="card-title-meta" style={{ cursor: "pointer" }} onClick={() => onJumpView("tareas")}>
                Ver todas →
              </button>
            </h3>
            <div className="task-list">
              {todayTasks.map(t => (
                <div key={t.project.id + t.id} className="task-line" onClick={() => onOpenProject(t.project.id)}>
                  <div className={`task-check ${t.done ? "done" : ""}`}
                    onClick={(e) => { e.stopPropagation(); onToggleTask(t.project.id, t.id); }}>
                    {t.done && I.check(11)}
                  </div>
                  <span style={{ fontSize: 13.5 }}>{t.name}</span>
                  <span className="task-project">{t.project.name}</span>
                  <span className="task-meta mono">{t.estimated || t.hours}h</span>
                </div>
              ))}
              {todayTasks.length === 0 && (
                <div className="section-empty" style={{ padding: 24 }}>
                  Sin tareas pendientes 🎉
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <h3 className="card-title">
              Próximos vencimientos
              <span className="card-title-meta">{upcoming.length}</span>
            </h3>
            <div className="upcoming">
              {upcoming.map(({ project, day, month }) => (
                <div key={project.id} className="up-row" onClick={() => onOpenProject(project.id)}>
                  <div className="up-date">
                    <div className="up-date-d">{day}</div>
                    <div className="up-date-m">{month}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 13.5, fontWeight: 500, display: "flex", alignItems: "center", gap: 6 }}>
                      {project.blocked && <span className="pcard-blocker" />}
                      {project.name}
                    </div>
                    <div style={{ fontSize: 11.5, color: "var(--fg-muted)", marginTop: 2 }}>
                      {D.STATE_LABEL[project.state]} · {project.actualHours}h / {project.estimatedHours}h
                    </div>
                  </div>
                  <span className={`pcard-priority priority-${project.priority}`}>{project.priority}</span>
                </div>
              ))}
              {upcoming.length === 0 && (
                <div className="section-empty" style={{ padding: 24 }}>
                  Sin deadlines próximos
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

// -------- Project card --------
function ProjectCard({ project, onOpen, onDragStart, onDragEnd }) {
  const ratio = project.actualHours / project.estimatedHours;
  const overClass = ratio > 1.3 ? "over" : ratio > 1 ? "warn" : "";
  return (
    <div
      className="pcard"
      draggable
      onDragStart={e => onDragStart(e, project)}
      onDragEnd={onDragEnd}
      onClick={() => onOpen(project.id)}
    >
      <div className="pcard-head">
        <div className="pcard-name">
          {project.blocked && <span className="pcard-blocker" />}
          {project.name}
        </div>
        <span className={`pcard-priority priority-${project.priority}`}>{project.priority}</span>
      </div>
      <p className="pcard-desc">{project.description}</p>
      <div className="pcard-hours">
        <span>{project.actualHours}h / {project.estimatedHours}h</span>
        <span>{ratio > 1 ? `+${Math.round((ratio - 1) * 100)}%` : `${Math.round(ratio * 100)}%`}</span>
      </div>
      <div className="pcard-bar">
        <div className={`pcard-bar-fill ${overClass}`} style={{ width: `${Math.min(ratio * 100, 100)}%` }} />
      </div>
      <div className="pcard-foot">
        <div className="tags">
          {project.tags.map(t => <span key={t} className="tag">{t}</span>)}
        </div>
        <span className="mono">{project.lastUpdate}</span>
      </div>
    </div>
  );
}

// -------- Kanban Columns --------
function KanbanColumns({ projects, onOpen, onMove }) {
  const [dragId, setDragId] = useState(null);
  const [dragOver, setDragOver] = useState(null);

  const grouped = useMemo(() => {
    const g = {};
    D.STATES.forEach(s => g[s] = []);
    projects.forEach(p => g[p.state].push(p));
    return g;
  }, [projects]);

  const onDragStart = (e, p) => {
    setDragId(p.id);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", p.id);
    e.currentTarget.classList.add("dragging");
  };
  const onDragEnd = e => {
    setDragId(null);
    setDragOver(null);
    e.currentTarget.classList.remove("dragging");
  };
  const onDragOver = (e, s) => { e.preventDefault(); setDragOver(s); };
  const onDrop = (e, s) => {
    e.preventDefault();
    const id = e.dataTransfer.getData("text/plain") || dragId;
    if (id) onMove(id, s);
    setDragOver(null);
  };

  return (
    <div className="kanban-columns">
      {D.STATES.map(state => (
        <div
          key={state}
          className={`kanban-col ${dragOver === state ? "drag-over" : ""}`}
          onDragOver={e => onDragOver(e, state)}
          onDragLeave={() => setDragOver(null)}
          onDrop={e => onDrop(e, state)}
        >
          <div className="kanban-col-head">
            <span className="kanban-col-title">{D.STATE_LABEL_SHORT[state]}</span>
            <span className="col-count">{grouped[state].length}</span>
          </div>
          <div className="kanban-col-body">
            {grouped[state].map(p => (
              <ProjectCard key={p.id} project={p} onOpen={onOpen}
                onDragStart={onDragStart} onDragEnd={onDragEnd} />
            ))}
            {grouped[state].length === 0 && (
              <div style={{ padding: "20px 8px", fontSize: 11, color: "var(--fg-subtle)", textAlign: "center" }}>
                Sin proyectos
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// -------- Kanban List --------
function KanbanList({ projects, onOpen }) {
  const grouped = useMemo(() => {
    const g = {};
    D.STATES.forEach(s => g[s] = []);
    projects.forEach(p => g[p.state].push(p));
    return g;
  }, [projects]);

  return (
    <div className="kanban-list">
      <div className="list-row" style={{ background: "transparent", border: "none", padding: "0 14px", cursor: "default", boxShadow: "none" }}>
        <span></span>
        <span className="list-cell label">Proyecto</span>
        <span className="list-cell label">Horas</span>
        <span className="list-cell label">Días</span>
        <span className="list-cell label">Deadline</span>
        <span></span>
      </div>
      {D.STATES.map(state => grouped[state].length > 0 && (
        <div key={state} className="list-group">
          <div className="list-group-head">
            <span className="list-group-name">{D.STATE_LABEL_SHORT[state]}</span>
            <span className="col-count">{grouped[state].length}</span>
            <div className="list-divider" />
          </div>
          {grouped[state].map(p => {
            const ratio = p.actualHours / p.estimatedHours;
            return (
              <div key={p.id} className="list-row" onClick={() => onOpen(p.id)}>
                <div className="list-state-dot" style={{ background: p.blocked ? "var(--danger)" : "var(--accent)" }} />
                <div className="list-name">
                  {p.blocked && <span className="pcard-blocker" />}
                  {p.name}
                  <span className="list-name-tags">· {p.tags.join(", ")}</span>
                </div>
                <div className="list-cell" style={ratio > 1.3 ? { color: "var(--danger)" } : {}}>
                  {p.actualHours}h / {p.estimatedHours}h
                </div>
                <div className="list-cell">{p.daysInState}d en {D.STATE_LABEL_SHORT[p.state].toLowerCase()}</div>
                <div className="list-cell">{p.deadline}</div>
                <span style={{ color: "var(--fg-subtle)" }}>{I.arrowRight(14)}</span>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

// -------- Kanban Timeline --------
function KanbanTimeline({ projects, onOpen }) {
  return (
    <div className="timeline">
      <div className="timeline-header">
        {D.STATES.map((s) => (
          <div key={s} className="tl-stage">
            <div className="tl-stage-name">{D.STATE_LABEL_SHORT[s]}</div>
            <div className="tl-stage-pip" />
            <div className="tl-stage-line" />
          </div>
        ))}
      </div>
      <div className="tl-rows">
        {projects.map(p => {
          const stageIdx = D.STATES.indexOf(p.state);
          const fillPct = ((stageIdx + 0.5) / D.STATES.length) * 100;
          return (
            <div key={p.id} className="tl-row" onClick={() => onOpen(p.id)} style={{ cursor: "pointer" }}>
              <div className="tl-row-label">
                {p.blocked && <span className="pcard-blocker" />}
                {p.name}
                <span className={`pcard-priority priority-${p.priority}`} style={{ fontSize: 8 }}>{p.priority}</span>
              </div>
              <div className="tl-row-track">
                <div className="tl-row-bar" />
                <div className="tl-row-fill" style={{ width: `${fillPct}%` }} />
                {D.STATES.map((_, i) => (
                  <div key={i} style={{ position: "relative", display: "flex", justifyContent: "center" }}>
                    {i === stageIdx && (
                      <div className={`tl-row-marker ${p.blocked ? "blocked" : ""}`} title={p.name} />
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// -------- New Project Modal --------
function NewProjectModal({ onClose, onSave }) {
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [priority, setPriority] = useState("media");
  const [hours, setHours] = useState("");
  const [fechaInicio, setFechaInicio] = useState("");
  const [deadline, setDeadline] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onSave({ name: name.trim(), description: desc.trim() || undefined, priority, estimatedHours: hours ? parseFloat(hours) : undefined, fechaInicio: fechaInicio || null, deadline: deadline || null });
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}
      onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: "var(--r-lg)", padding: 28, width: 420, maxWidth: "90vw" }}>
        <h2 style={{ margin: "0 0 20px", fontSize: 16, fontWeight: 600 }}>Nuevo proyecto</h2>
        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Nombre *</label>
            <input autoFocus value={name} onChange={e => setName(e.target.value)} placeholder="Ej: APODERAR" required
              style={{ width: "100%", boxSizing: "border-box", padding: "8px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 14 }} />
          </div>
          <div>
            <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Descripción</label>
            <input value={desc} onChange={e => setDesc(e.target.value)} placeholder="Descripción breve (opcional)"
              style={{ width: "100%", boxSizing: "border-box", padding: "8px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 14 }} />
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Prioridad</label>
              <select value={priority} onChange={e => setPriority(e.target.value)}
                style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 14 }}>
                <option value="baja">Baja</option>
                <option value="media">Media</option>
                <option value="alta">Alta</option>
                <option value="critica">Crítica</option>
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Horas estimadas</label>
              <input type="number" min="0" step="0.5" value={hours} onChange={e => setHours(e.target.value)} placeholder="Ej: 10"
                style={{ width: "100%", boxSizing: "border-box", padding: "8px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 14 }} />
            </div>
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Fecha de inicio</label>
              <input type="date" value={fechaInicio} onChange={e => setFechaInicio(e.target.value)}
                style={{ width: "100%", boxSizing: "border-box", padding: "8px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 14 }} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Fecha de vencimiento</label>
              <input type="date" value={deadline} onChange={e => setDeadline(e.target.value)}
                style={{ width: "100%", boxSizing: "border-box", padding: "8px 10px", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--bg-base)", color: "var(--text-primary)", fontSize: 14 }} />
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 8 }}>
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={saving || !name.trim()}>
              {saving ? "Guardando…" : `${I.folder(14)} Crear proyecto`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// -------- Projects section --------
function ProjectsSection({ projects, kanbanView, setKanbanView, onOpenProject, onMoveProject, onAddProject }) {
  const [showArchived, setShowArchived] = useState(false);
  const activeProjects = useMemo(() => projects.filter(p => showArchived ? p.archived : !p.archived), [projects, showArchived]);
  const archivedCount = useMemo(() => projects.filter(p => p.archived).length, [projects]);
  const isEmpty = activeProjects.length === 0;
  const [showModal, setShowModal] = useState(false);
  const [selectedTags, setSelectedTags] = useState([]);

  const allTags = useMemo(() => {
    const set = new Set();
    activeProjects.forEach(p => p.tags.forEach(t => set.add(t)));
    return [...set].sort();
  }, [activeProjects]);

  const visibleProjects = useMemo(() => {
    if (selectedTags.length === 0) return activeProjects;
    return activeProjects.filter(p => selectedTags.some(t => p.tags.includes(t)));
  }, [activeProjects, selectedTags]);

  const toggleTag = (tag) => {
    setSelectedTags(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]);
  };

  const handleSave = async (payload) => {
    await onAddProject(payload);
  };

  return (
    <section className="section">
      {showModal && <NewProjectModal onClose={() => setShowModal(false)} onSave={handleSave} />}
      <div className="section-head">
        <div>
          <div className="section-eyebrow">Proyectos</div>
          <h1 className="section-title">Estado de proyectos</h1>
          <p className="section-subtitle">
            {isEmpty
              ? (showArchived ? "Sin proyectos archivados" : "Todavía no creaste ningún proyecto")
              : `${visibleProjects.length}${selectedTags.length ? ` de ${activeProjects.length}` : ""} proyectos${showArchived ? " archivados" : ""} · arrastrá entre columnas para cambiar de estado`}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {archivedCount > 0 && (
            <button className={`btn btn-ghost`} style={{ height: 34, fontSize: 12, color: showArchived ? "var(--accent)" : "var(--fg-muted)" }}
              onClick={() => setShowArchived(v => !v)}>
              {showArchived ? "Ver activos" : `Archivados (${archivedCount})`}
            </button>
          )}
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>{I.folder(14)} Nuevo proyecto</button>
          {!isEmpty && (
            <div className="view-switch">
              <button className={kanbanView === "columns" ? "active" : ""} onClick={() => setKanbanView("columns")}>
                {I.columns(13)} Columnas
              </button>
              <button className={kanbanView === "list" ? "active" : ""} onClick={() => setKanbanView("list")}>
                {I.list(13)} Lista
              </button>
              <button className={kanbanView === "timeline" ? "active" : ""} onClick={() => setKanbanView("timeline")}>
                {I.timelineIcon(13)} Timeline
              </button>
            </div>
          )}
        </div>
      </div>

      {!isEmpty && allTags.length > 0 && (
        <div className="filter-bar" style={{ marginBottom: 16 }}>
          <span style={{ fontSize: 11, color: "var(--fg-muted)", marginRight: 4, alignSelf: "center" }}>Tags:</span>
          {allTags.map(tag => (
            <button key={tag} className={`filter-chip ${selectedTags.includes(tag) ? "active" : ""}`}
              onClick={() => toggleTag(tag)}>
              {tag}
            </button>
          ))}
          {selectedTags.length > 0 && (
            <button className="filter-chip" style={{ color: "var(--fg-muted)" }} onClick={() => setSelectedTags([])}>
              × limpiar
            </button>
          )}
        </div>
      )}

      {isEmpty && (
        <div className="empty-hero">
          <div className="empty-hero-mark">{I.folder(28)}</div>
          <h2>Sin proyectos todavía</h2>
          <p>
            Cuando crees el primero vas a ver acá el Kanban con sus 5 estados:<br />
            análisis → desarrollo → testing → listo → producción.
          </p>
          <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
            <button className="btn btn-primary" onClick={() => setShowModal(true)}>{I.folder(14)} Crear proyecto</button>
          </div>
        </div>
      )}

      {!isEmpty && kanbanView === "columns" && (
        <KanbanColumns projects={visibleProjects} onOpen={onOpenProject} onMove={onMoveProject} />
      )}
      {!isEmpty && kanbanView === "list" && (
        <KanbanList projects={visibleProjects} onOpen={onOpenProject} />
      )}
      {!isEmpty && kanbanView === "timeline" && (
        <KanbanTimeline projects={visibleProjects} onOpen={onOpenProject} />
      )}
    </section>
  );
}

window.MAESTRO_DASH = { Header, HomeSection, ProjectsSection, NAV };
