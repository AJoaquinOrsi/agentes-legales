// =====================================================================
// MAESTRO — App shell (real API integration)
// =====================================================================
const { useState: useStateApp, useEffect: useEffectApp, useMemo: useMemoApp, useCallback: useCallbackApp, useRef: useRefApp, useReducer: useReducerApp } = React;
const D_app = window.MAESTRO_DATA;
const I_app = window.MAESTRO_ICONS;
const { Header, HomeSection, ProjectsSection } = window.MAESTRO_DASH;
const { Drawer, Login } = window.MAESTRO_DL;
const { ProjectDetail } = window.MAESTRO_DETAIL;
const { TareasSection, CalendarioSection, StatsSection, AsistenteSection, ConfigSection } = window.MAESTRO_SECTIONS;
const { TweaksPanel, useTweaks, TweakSection, TweakRadio, TweakToggle, TweakSelect, TweakRow } = window;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accentHue": 280,
  "density": "cozy",
  "kanbanView": "columns",
  "showAvatars": true,
  "agentTone": "Cálido coach",
  "theme": "light",
  "initialView": "inicio",
  "demoData": false
}/*EDITMODE-END*/;

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);

  // ----- App state
  const [logged, setLogged] = useStateApp(() => !!D_app.getToken());
  const [currentUser, setCurrentUser] = useStateApp(null);
  const [view, setView] = useStateApp(t.initialView || "inicio");
  const [theme, setTheme] = useStateApp(t.theme || "light");
  const [projects, setProjects] = useStateApp([]);
  const [loading, setLoading] = useStateApp(true);
  const [messages, setMessages] = useStateApp(
    D_app.INITIAL_CHAT.map(m => ({ ...m, id: m.id || `m-${Math.random()}` }))
  );
  const [conversationHistory, setConversationHistory] = useStateApp([]);
  const [openProjectId, setOpenProjectId] = useStateApp(null);
  const [openDetailId, setOpenDetailId] = useStateApp(null);
  const [activeTimer, setActiveTimer] = useStateApp(null);
  const [timerTick, setTimerTick] = useStateApp(0);
  const timerIntervalRef = useRefApp(null);

  const handleOpenDetail = useCallbackApp((id) => {
    setOpenDetailId(id);
    setOpenProjectId(null);
  }, []);
  const [kanbanView, setKanbanView] = useStateApp(t.kanbanView || "columns");
  const [toasts, setToasts] = useStateApp([]);
  const [chatSessions, setChatSessions] = useStateApp([]);
  const [currentSessionId, setCurrentSessionId] = useStateApp(null);

  // ----- Handle session expiry (401 from any API call)
  useEffectApp(() => {
    const onUnauthorized = () => {
      D_app.clearToken();
      setLogged(false);
      setCurrentUser(null);
      addToast("Sesión expirada. Volvé a iniciar sesión.", "warning");
    };
    window.addEventListener("maestro:unauthorized", onUnauthorized);
    return () => window.removeEventListener("maestro:unauthorized", onUnauthorized);
  }, []);

  // ----- Reload events from project-detail / sections
  useEffectApp(() => {
    if (!logged) return;
    const onReloadProject = async (e) => {
      const projectId = e.detail?.projectId;
      if (!projectId) return;
      const detail = await enrichProject(projectId);
      if (detail) setProjects(prev => prev.map(p => p.id === projectId ? { ...p, ...detail } : p));
    };
    const onReloadProjects = () => { loadProjects(); };
    window.addEventListener("maestro:reloadProject", onReloadProject);
    window.addEventListener("maestro:reloadProjects", onReloadProjects);
    return () => {
      window.removeEventListener("maestro:reloadProject", onReloadProject);
      window.removeEventListener("maestro:reloadProjects", onReloadProjects);
    };
  }, [logged]);

  // ----- Auto-logout timer + expiry warning
  useEffectApp(() => {
    if (!logged) return;
    const token = D_app.getToken();
    const expiresAt = D_app.getTokenExpiry(token);
    if (!expiresAt) return;

    const now = Date.now();
    const msLeft = expiresAt - now;
    if (msLeft <= 0) {
      D_app.clearToken(); setLogged(false); setCurrentUser(null); return;
    }

    const WARN_MS = 10 * 60 * 1000; // warn 10 min before expiry
    const timers = [];

    if (msLeft > WARN_MS) {
      timers.push(setTimeout(() => {
        addToast("Tu sesión expira en 10 minutos. Guardá tu trabajo.", "warning");
      }, msLeft - WARN_MS));
    }

    timers.push(setTimeout(() => {
      D_app.clearToken();
      setLogged(false);
      setCurrentUser(null);
      addToast("Sesión expirada. Volvé a iniciar sesión.", "warning");
    }, msLeft));

    return () => timers.forEach(clearTimeout);
  }, [logged]);

  // ----- Reminders: check deadlines and blockers once per session
  useEffectApp(() => {
    if (!logged || projects.length === 0) return;
    const shown = sessionStorage.getItem("maestro_reminders_shown");
    if (shown) return;
    sessionStorage.setItem("maestro_reminders_shown", "1");
    const todayISO = new Date().toISOString().split("T")[0];
    const in3Days = new Date(); in3Days.setDate(in3Days.getDate() + 3);
    const in3ISO = in3Days.toISOString().split("T")[0];
    projects.forEach(p => {
      if (p.archived) return;
      if (p.deadline && p.deadline >= todayISO && p.deadline <= in3ISO) {
        const days = Math.ceil((new Date(p.deadline) - new Date()) / 86400000);
        setTimeout(() => toast(`Deadline en ${days}d: ${p.name}`, "warning"), 500);
      }
      const oldBlockers = (p.blockers || []).filter(b => !b.resolved && b.days >= 2);
      if (oldBlockers.length > 0) {
        setTimeout(() => toast(`Bloqueo sin resolver en ${p.name} (${oldBlockers[0].days}d)`, "warning"), 800);
      }
    });
  }, [logged, projects]);

  // ----- Load sessions on login
  useEffectApp(() => {
    if (logged && !t.demoData) {
      D_app.API.apiFetch("/chat/sessions").then(s => setChatSessions(s)).catch(() => {});
    }
  }, [logged, t.demoData]);

  // ----- Demo mode toggle
  useEffectApp(() => {
    if (t.demoData) {
      setProjects(D_app.DEMO_PROJECTS);
      setMessages(D_app.DEMO_CHAT.map(m => ({ ...m, id: m.id || `m-${Math.random()}` })));
      setConversationHistory([]);
      setLoading(false);
    } else if (logged) {
      loadProjects();
    }
  }, [t.demoData, logged]);

  // ----- Load real projects from API
  async function loadProjects() {
    setLoading(true);
    try {
      const data = await D_app.API.getProjects();
      const uiProjects = data.map(D_app.apiProjectToUI);
      setProjects(uiProjects);

      // Also load tasks/blockers/notes per project (detail endpoint)
      const details = await Promise.allSettled(
        uiProjects.map(p => enrichProject(p.id))
      );
      setProjects(prev =>
        prev.map((p, i) => {
          if (details[i].status !== "fulfilled") return p;
          const d = details[i].value;
          // Merge: keep state changes from apiProjectToUI + add hours events
          const merged = [...p.history, ...(d.hoursHistory || [])];
          return { ...p, ...d, history: merged };
        })
      );

      // Daily report: once per day, show an AI-generated summary in the chat
      const today = new Date().toDateString();
      const lastReport = localStorage.getItem("maestro_daily_summary_date");
      if (lastReport !== today) {
        localStorage.setItem("maestro_daily_summary_date", today);
        setTimeout(() => {
          D_app.buildAgentReply(
            "Buenos días. Dame un resumen breve del estado actual: proyectos activos, si hay alguno en riesgo y cuáles son las tareas más urgentes.",
            { conversationHistory: [], _newHistory: null, _toolsExecuted: [] }
          ).then(reply => {
            const dailyMsg = {
              id: "daily-" + Date.now(),
              ...reply,
              time: new Date().toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" }),
            };
            setMessages(ms => [...ms, dailyMsg]);
          }).catch(() => {});
        }, 1800);
      }
    } catch (err) {
      console.error("Error cargando proyectos:", err);
      toast("No se pudo conectar al servidor", "error");
    } finally {
      setLoading(false);
    }
  }

  async function enrichProject(id) {
    try {
      const [tasks, blockers, notes, hours] = await Promise.all([
        D_app.API.apiFetch(`/projects/${id}/tasks`),
        D_app.API.apiFetch(`/projects/${id}/blockers`),
        D_app.API.apiFetch(`/projects/${id}/notes`),
        D_app.API.apiFetch(`/projects/${id}/hours`),
      ]);
      return {
        tasks: tasks.map(t => ({
          id: t.id,
          name: t.descripcion,
          done: t.completada,
          hours: 0,
          estimated: t.estimated_hours || 2,
          fechaInicio: t.fecha_inicio || null,
          fechaVencimiento: t.fecha_vencimiento || null,
          _apiId: t.id,
        })),
        blockers: blockers.map(b => ({
          id: b.id,
          desc: b.descripcion,
          type: b.tipo,
          createdAt: b.created_at,
          days: b.dias_sin_resolver,
          resolved: b.resuelto,
          _apiId: b.id,
        })),
        notes: notes.map(n => ({
          id: n.id,
          text: n.contenido,
          type: n.tipo,
          date: n.created_at ? new Date(n.created_at).toLocaleDateString("es-AR") : "",
        })),
        rawHours: hours.map(h => ({ fecha: String(h.fecha), horas: h.horas })),
        hoursHistory: hours.slice(0, 10).map(h => ({
          time: new Date(h.fecha).toLocaleDateString("es-AR", { day: "2-digit", month: "short" }),
          text: `+${h.horas}h${h.descripcion ? ` — ${h.descripcion}` : ""}`,
          type: "time",
        })),
      };
    } catch {
      return {};
    }
  }

  // ----- Timer interval
  useEffectApp(() => {
    if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    if (activeTimer) {
      timerIntervalRef.current = setInterval(() => setTimerTick(n => n + 1), 1000);
    }
    return () => { if (timerIntervalRef.current) clearInterval(timerIntervalRef.current); };
  }, [activeTimer ? activeTimer.taskId : null]);

  function formatTimer(s) {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) return `${h}:${String(m).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
    return `${String(m).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
  }

  const timerDisplaySeconds = activeTimer
    ? activeTimer.baseElapsed + Math.floor((Date.now() - activeTimer.startedAt) / 1000)
    : 0;

  useEffectApp(() => {}, [timerTick]); // force re-render on tick

  useEffectApp(() => {
    setTheme(t.theme || "light");
  }, [t.theme]);

  useEffectApp(() => {
    setKanbanView(t.kanbanView || "columns");
  }, [t.kanbanView]);

  useEffectApp(() => {
    document.documentElement.style.setProperty("--accent-h", String(t.accentHue));
    document.documentElement.setAttribute("data-density", t.density);
    document.documentElement.setAttribute("data-theme", theme);
  }, [t.accentHue, t.density, theme]);

  // ----- Toast helper
  const toast = useCallbackApp((text, kind = "success") => {
    const id = "t-" + Math.random();
    setToasts(ts => [...ts, { id, text, kind }]);
    setTimeout(() => setToasts(ts => ts.filter(x => x.id !== id)), 2800);
  }, []);

  // ----- Today summary derived (real hours from rawHours)
  const todaySummary = useMemoApp(() => {
    const today = new Date().toISOString().split("T")[0];
    const todayHours = projects.reduce((sum, p) => {
      return sum + (p.rawHours || [])
        .filter(h => h.fecha === today)
        .reduce((s, h) => s + h.horas, 0);
    }, 0);
    return {
      todayHours,
      tasksDone: projects.flatMap(p => p.tasks).filter(t => t.done).length,
      projectsTouched: projects.filter(p => p.actualHours > 0).length,
    };
  }, [projects]);

  // ----- Risk count
  const alertCount = projects.filter(
    p => p.blocked || p.actualHours > p.estimatedHours * 1.4 || p.daysInState > 4
  ).length;

  // ----- Optimistic update helpers
  function updateProject(id, updater) {
    setProjects(ps => ps.map(p => p.id === id ? updater(p) : p));
  }

  // ----- Action executors (call API, then update local state)
  const exec = useCallbackApp(async (action, payload) => {
    if (t.demoData) {
      // Demo mode: local only
      switch (action) {
        case "ADD_HOURS":
          updateProject(payload.projectId, p => ({
            ...p, actualHours: +(p.actualHours + payload.hours).toFixed(1),
            history: [{ time: "ahora", text: `Agregaste ${payload.hours}h`, type: "time" }, ...p.history],
          }));
          toast(`+${payload.hours}h en ${projects.find(x => x.id === payload.projectId)?.name}`);
          break;
        case "CHANGE_STATE":
          updateProject(payload.projectId, p => ({
            ...p, state: payload.newState, daysInState: 0,
            history: [{ time: "ahora", text: `Estado → ${D_app.STATE_LABEL[payload.newState]}`, type: "state" }, ...p.history],
          }));
          toast(`→ ${D_app.STATE_LABEL_SHORT[payload.newState]}`);
          break;
        case "ADD_BLOCKER":
          updateProject(payload.projectId, p => ({
            ...p, blocked: true,
            blockers: [{ id: "b-" + Math.random(), desc: payload.desc, type: "acceso", createdAt: "hoy", days: 0, resolved: false }, ...p.blockers],
            history: [{ time: "ahora", text: `Bloqueador: ${payload.desc}`, type: "blocker" }, ...p.history],
          }));
          toast("Bloqueador registrado", "warning");
          break;
        case "RESOLVE_BLOCKER":
          updateProject(payload.projectId, p => ({
            ...p, blocked: false,
            blockers: p.blockers.map(b => ({ ...b, resolved: true })),
            history: [{ time: "ahora", text: "Bloqueador resuelto", type: "blocker" }, ...p.history],
          }));
          toast("Bloqueador resuelto ✓");
          break;
        case "ADD_TASK": {
          updateProject(payload.projectId, p => ({
            ...p, tasks: [...p.tasks, { id: "t-" + Math.random(), name: payload.taskName, done: false, hours: 0, estimated: 2 }],
            history: [{ time: "ahora", text: `Tarea: ${payload.taskName}`, type: "task" }, ...p.history],
          }));
          toast("Tarea creada");
          break;
        }
        case "ADD_PROJECT": {
          const np = {
            id: "p-" + Date.now(), name: payload.name, description: "Nuevo proyecto.",
            state: "analisis", priority: "media", estimatedHours: 10, actualHours: 0,
            daysInState: 0, blocked: false, deadline: "—", tags: [], lastUpdate: "ahora",
            velocity: 0, tasks: [], blockers: [], notes: [], links: [],
            history: [{ time: "ahora", text: "Proyecto creado", type: "state" }],
          };
          setProjects(ps => [np, ...ps]);
          toast(`Proyecto ${payload.name} creado`);
          break;
        }
      }
      return;
    }

    // Real API mode
    try {
      switch (action) {
        case "ADD_HOURS": {
          const proj = projects.find(x => x.id === payload.projectId);
          if (!proj) return;
          await D_app.API.addHours(proj.id, payload.hours, payload.description || "");
          const todayISO = new Date().toISOString().split("T")[0];
          updateProject(proj.id, p => ({
            ...p,
            actualHours: +(p.actualHours + payload.hours).toFixed(1),
            rawHours: [...(p.rawHours || []), { fecha: todayISO, horas: payload.hours }],
            workHours: [...(p.workHours || []), {
              id: "wh-" + Date.now(),
              hours: payload.hours,
              date: todayISO,
              desc: payload.description || null,
              createdAt: new Date().toISOString(),
            }],
            history: [{ time: "ahora", text: `+${payload.hours}h`, type: "time" }, ...p.history],
          }));
          toast(`+${payload.hours}h en ${proj.name}`);
          break;
        }
        case "CHANGE_STATE": {
          const proj = projects.find(x => x.id === payload.projectId);
          if (!proj) return;
          const apiState = D_app.INTERNAL_STATE_MAP[payload.newState];
          await D_app.API.changeStatus(proj.id, apiState, payload.razon);
          updateProject(proj.id, p => ({
            ...p, state: payload.newState, daysInState: 0,
            history: [{ time: "ahora", text: `Estado → ${D_app.STATE_LABEL[payload.newState]}`, type: "state" }, ...p.history],
          }));
          toast(`${proj.name} → ${D_app.STATE_LABEL_SHORT[payload.newState]}`);
          break;
        }
        case "ADD_BLOCKER": {
          const proj = projects.find(x => x.id === payload.projectId);
          if (!proj) return;
          const blocker = await D_app.API.createBlocker(proj.id, payload.desc, payload.tipo || "otro");
          updateProject(proj.id, p => ({
            ...p, blocked: true,
            blockers: [{ id: blocker.id, desc: blocker.descripcion, type: blocker.tipo, createdAt: "hoy", days: 0, resolved: false }, ...p.blockers],
            history: [{ time: "ahora", text: `Bloqueador: ${payload.desc}`, type: "blocker" }, ...p.history],
          }));
          toast("Bloqueador registrado", "warning");
          break;
        }
        case "RESOLVE_BLOCKER": {
          const proj = projects.find(x => x.id === payload.projectId);
          if (!proj) return;
          const targetBlocker = payload.blockerId
            ? proj.blockers.find(b => b.id === payload.blockerId)
            : proj.blockers.find(b => !b.resolved);
          if (targetBlocker) {
            await D_app.API.resolveBlocker(proj.id, targetBlocker.id);
          }
          updateProject(proj.id, p => ({
            ...p, blocked: false,
            blockers: p.blockers.map(b => ({ ...b, resolved: true })),
            history: [{ time: "ahora", text: "Bloqueador resuelto", type: "blocker" }, ...p.history],
          }));
          toast("Bloqueador resuelto ✓");
          break;
        }
        case "ADD_TASK": {
          const proj = projects.find(x => x.id === payload.projectId);
          if (!proj) return;
          const task = await D_app.API.createTask(
            proj.id, payload.taskName, "media",
            payload.fechaInicio || null, payload.fechaVencimiento || null,
            payload.taskType || "task", payload.meetingWith || null
          );
          if (payload.prepFile) {
            try {
              const updated = await D_app.API.uploadTaskPrepFile(proj.id, task.id, payload.prepFile);
              task.meeting_prep_url = updated.meeting_prep_url;
              task.meeting_prep_filename = updated.meeting_prep_filename;
            } catch (e) { console.error("prep file upload:", e); }
          }
          updateProject(proj.id, p => ({
            ...p,
            tasks: [...p.tasks, {
              id: task.id, name: task.descripcion, done: false, hours: 0, estimated: task.estimated_hours || 2,
              fechaInicio: task.fecha_inicio || null, fechaVencimiento: task.fecha_vencimiento || null,
              taskType: task.task_type || "task", meetingWith: task.meeting_with || null,
              meetingPrepUrl: task.meeting_prep_url || null, meetingPrepFilename: task.meeting_prep_filename || null,
              elapsedSeconds: 0, timerStartedAt: null, subtareas: [],
            }],
            history: [{ time: "ahora", text: `${payload.taskType === "meeting" ? "Reunión" : "Tarea"}: ${payload.taskName}`, type: "task" }, ...p.history],
          }));
          toast(payload.taskType === "meeting" ? "Reunión creada" : "Tarea creada");
          break;
        }
        case "ADD_PROJECT": {
          const newProj = await D_app.API.createProject({
            nombre: payload.name,
            descripcion: payload.description || undefined,
            cliente_area: payload.clienteArea || "General",
            prioridad: payload.priority || "media",
            estimated_hours: payload.estimatedHours || undefined,
            fecha_inicio: payload.fechaInicio || undefined,
            deadline: payload.deadline || undefined,
          });
          const uiProj = D_app.apiProjectToUI(newProj);
          setProjects(ps => [{ ...uiProj, tasks: [], blockers: [], notes: [], rawHours: [], history: [{ time: "ahora", text: "Proyecto creado", type: "state" }] }, ...ps]);
          toast(`Proyecto ${payload.name} creado`);
          break;
        }
        case "EDIT_PROJECT": {
          await D_app.API.apiFetch(`/projects/${payload.projectId}`, {
            method: "PATCH",
            body: JSON.stringify(payload.updates),
          });
          updateProject(payload.projectId, p => ({
            ...p,
            description: payload.updates.descripcion !== undefined ? payload.updates.descripcion : p.description,
            priority: payload.updates.prioridad || p.priority,
            estimatedHours: payload.updates.estimated_hours !== undefined ? payload.updates.estimated_hours : p.estimatedHours,
            deadline: payload.updates.deadline !== undefined ? payload.updates.deadline : p.deadline,
            fechaInicio: payload.updates.fecha_inicio !== undefined ? payload.updates.fecha_inicio : p.fechaInicio,
            responsable: payload.updates.responsable !== undefined ? payload.updates.responsable : p.responsable,
            specsText: payload.updates.specs_text !== undefined ? payload.updates.specs_text : p.specsText,
            links: payload.updates.links_json !== undefined
              ? (() => { try { return JSON.parse(payload.updates.links_json || "[]"); } catch { return p.links; } })()
              : p.links,
            structureText: payload.updates.structure_text !== undefined ? payload.updates.structure_text : p.structureText,
            structureImageUrl: payload.updates.structure_image_url !== undefined ? payload.updates.structure_image_url : p.structureImageUrl,
            tarifaHora: payload.updates.tarifa_hora !== undefined ? payload.updates.tarifa_hora : p.tarifaHora,
            presupuesto: payload.updates.presupuesto !== undefined ? payload.updates.presupuesto : p.presupuesto,
          }));
          toast("Proyecto actualizado");
          break;
        }
        case "DELETE_PROJECT": {
          await D_app.API.apiFetch(`/projects/${payload.projectId}`, { method: "DELETE" });
          setProjects(ps => ps.filter(p => p.id !== payload.projectId));
          toast("Proyecto eliminado");
          break;
        }
        case "ARCHIVE_PROJECT": {
          await D_app.API.updateProject(payload.projectId, { archived: !payload.currentArchived });
          updateProject(payload.projectId, p => ({ ...p, archived: !payload.currentArchived }));
          toast(payload.currentArchived ? "Proyecto desarchivado" : "Proyecto archivado");
          break;
        }
        case "DUPLICATE_PROJECT": {
          const src = projects.find(x => x.id === payload.projectId);
          if (!src) return;
          const newProj = await D_app.API.createProject({
            nombre: src.name + " (copia)",
            descripcion: src.description,
            cliente_area: src.clientArea || "General",
            prioridad: src.priority,
            estimated_hours: src.estimatedHours,
            fecha_inicio: src.fechaInicio || undefined,
            deadline: src.deadline || undefined,
            responsable: src.responsable || undefined,
            specs_text: src.specsText || undefined,
            tags: (src.tags || []).join(",") || undefined,
          });
          const uiProj = D_app.apiProjectToUI(newProj);
          setProjects(ps => [{ ...uiProj, tasks: [], blockers: [], notes: [], rawHours: [], history: [] }, ...ps]);
          toast(`Proyecto duplicado: ${newProj.nombre}`);
          break;
        }
        case "UPDATE_TASK_SUBTASKS": {
          const proj = projects.find(x => x.id === payload.projectId);
          if (!proj) return;
          await D_app.API.updateTask(proj.id, payload.taskId, { subtareas_json: JSON.stringify(payload.subtareas) });
          updateProject(proj.id, p => ({
            ...p,
            tasks: p.tasks.map(t => t.id === payload.taskId ? { ...t, subtareas: payload.subtareas } : t),
          }));
          break;
        }
        case "ADD_NOTE": {
          const proj = projects.find(x => x.id === payload.projectId);
          if (!proj) return;
          await D_app.API.addNote(proj.id, payload.contenido, payload.tipo || "otro");
          updateProject(proj.id, p => ({
            ...p,
            notes: [...p.notes, {
              id: "n-" + Date.now(),
              text: payload.contenido,
              type: payload.tipo || "otro",
              date: new Date().toLocaleDateString("es-AR"),
            }],
            history: [{ time: "ahora", text: `Nota: ${payload.contenido.slice(0, 40)}`, type: "note" }, ...p.history],
          }));
          toast("Nota guardada");
          break;
        }
      }
    } catch (err) {
      console.error("exec error:", err);
      toast(`Error: ${err.message}`, "error");
    }
  }, [projects, toast, t.demoData]);

  // ----- Send message → async agent reply
  const onSend = useCallbackApp(async (text) => {
    const userMsg = {
      id: "u-" + Date.now(),
      role: "user",
      text,
      time: new Date().toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" }),
    };
    const thinkingId = "thinking-" + Date.now();
    const thinking = { id: thinkingId, role: "agent", thinking: true };
    setMessages(ms => [...ms, userMsg, thinking]);

    const ctx = {
      projects,
      conversationHistory,
      ...todaySummary,
      _newHistory: null,
      _toolsExecuted: [],
    };

    const reply = await D_app.buildAgentReply(text, ctx);
    const replyMsg = {
      id: "a-" + Date.now(),
      ...reply,
      time: new Date().toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages(ms => ms.filter(m => m.id !== thinkingId).concat(replyMsg));

    // Update conversation history for multi-turn
    if (ctx._newHistory) {
      setConversationHistory(ctx._newHistory);
    }

    // Persist session after each exchange
    if (!t.demoData && ctx._newHistory && ctx._newHistory.length > 0) {
      const newMsgs = [...messages.filter(m => m.id !== thinkingId && !m.thinking), userMsg, replyMsg];
      const sessionName = userMsg.text.slice(0, 60);
      D_app.API.apiFetch("/chat/sessions", {
        method: "POST",
        body: JSON.stringify({
          session_id: currentSessionId || undefined,
          name: sessionName,
          messages: newMsgs.filter(m => m.role && m.text),
          api_history: ctx._newHistory,
        }),
      }).then(saved => {
        setCurrentSessionId(saved.id);
        setChatSessions(prev => {
          const exists = prev.find(s => s.id === saved.id);
          const updated = { ...saved, preview: replyMsg.text?.slice(0, 60) || "" };
          return exists ? prev.map(s => s.id === saved.id ? updated : s) : [updated, ...prev];
        });
      }).catch(() => {});
    }

    // If agent executed tools, refresh projects from API
    if (!t.demoData && ctx._toolsExecuted && ctx._toolsExecuted.length > 0) {
      const writes = ["create_project", "update_project_status", "add_work_hours",
        "create_task", "complete_task", "create_blocker", "resolve_blocker", "add_note"];
      if (ctx._toolsExecuted.some(tool => writes.includes(tool))) {
        setTimeout(() => loadProjects(), 300);
      }
    }
  }, [projects, todaySummary, conversationHistory, t.demoData]);

  // ----- Confirm/cancel inline (demo mode — in real mode agent handles it)
  const onConfirm = useCallbackApp((msgId, yes) => {
    setMessages(ms => ms.map(m => m.id === msgId ? { ...m, resolved: yes ? "yes" : "no" } : m));
    if (!yes) {
      setTimeout(() => {
        setMessages(ms => [...ms, {
          id: "c-" + Date.now(),
          role: "agent",
          text: "Listo, cancelado. ¿Otra cosa? 🙌",
          time: new Date().toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" }),
        }]);
      }, 300);
      return;
    }
    const original = messages.find(m => m.id === msgId);
    if (!original?.confirm) return;
    exec(original.confirm.action, original.confirm.payload);
    setTimeout(() => {
      const action = original.confirm.action;
      const payload = original.confirm.payload;
      const p = projects.find(x => x.id === payload.projectId);
      let followText = "Listo ✓";
      let followBlock;
      if (action === "ADD_HOURS" && p) {
        const newH = +(p.actualHours + payload.hours).toFixed(1);
        const ratio = newH / p.estimatedHours;
        followBlock = { title: "📊 Análisis", items: [["Total en " + p.name, `${newH}h`], ["vs Estimado", `${p.estimatedHours}h`], ["Diferencia", ratio > 1 ? `+${Math.round((ratio - 1) * 100)}%` : `${Math.round(ratio * 100)}%`]] };
        followText = ratio > 1.3 ? `Registré las horas. Ojo: ya estás ${Math.round((ratio - 1) * 100)}% por encima del estimado 📝` : "Registré las horas. Vas bien, queda margen 👌";
      } else if (action === "CHANGE_STATE" && p) {
        followText = `${p.name} ahora está en ${D_app.STATE_LABEL[payload.newState]}. Buen ritmo!`;
      } else if (action === "ADD_TASK") {
        followText = "Tarea agregada al backlog ✓";
      } else if (action === "ADD_BLOCKER") {
        followText = "Bloqueador registrado ✓ Te aviso si pasan 2 días sin resolución.";
      } else if (action === "RESOLVE_BLOCKER" && p) {
        followText = `${p.name} está desbloqueado 🎉 ¿Lo retomás hoy?`;
      } else if (action === "ADD_PROJECT") {
        followText = `Creé el proyecto ✓ Arrancando en análisis. ¿Le agrego tareas iniciales?`;
      }
      setMessages(ms => [...ms, {
        id: "f-" + Date.now(), role: "agent", text: followText, block: followBlock,
        time: new Date().toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" }),
      }]);
    }, 500);
  }, [messages, projects, exec]);

  // ----- Request AI insights (for StatsSection)
  const onRequestInsights = useCallbackApp(async () => {
    try {
      const result = await D_app.API.chat(
        "Analizá mi performance y dame exactamente 4 insights breves (máximo 2 oraciones cada uno): uno sobre proyectos en riesgo, uno sobre eficiencia de horas, uno sobre velocity y uno con una recomendación concreta.",
        []
      );
      return result.respuesta;
    } catch {
      return null;
    }
  }, []);

  // ----- Sync calendar (for CalendarioSection)
  const onSyncCalendar = useCallbackApp(async () => {
    try {
      const result = await D_app.API.chat(
        "Sincronizá los deadlines de todos mis proyectos con Google Calendar.",
        []
      );
      return result.respuesta;
    } catch {
      return "Error al sincronizar. Verificá la integración con Google Calendar en Configuración.";
    }
  }, []);

  // ----- Toggle task
  const onToggleTask = useCallbackApp(async (projectId, taskId) => {
    updateProject(projectId, p => ({
      ...p, tasks: p.tasks.map(t => t.id === taskId ? { ...t, done: !t.done } : t),
    }));
    if (!t.demoData) {
      const proj = projects.find(x => x.id === projectId);
      const task = proj?.tasks.find(t => t.id === taskId);
      if (proj && task && !task.done) {
        try { await D_app.API.completeTask(proj.id, task.id); } catch (e) { console.error(e); }
      }
    }
  }, [projects, t.demoData]);

  // ----- Timer handlers
  const onStartTimer = useCallbackApp(async (projectId, taskId) => {
    if (t.demoData) return;
    if (activeTimer) {
      try {
        await D_app.API.pauseTimer(activeTimer.projectId, activeTimer.taskId);
        const elapsed = activeTimer.baseElapsed + Math.floor((Date.now() - activeTimer.startedAt) / 1000);
        updateProject(activeTimer.projectId, p => ({
          ...p, tasks: p.tasks.map(tk => tk.id === activeTimer.taskId ? { ...tk, elapsedSeconds: elapsed, timerStartedAt: null } : tk),
        }));
      } catch (e) { console.error(e); }
    }
    const proj = projects.find(x => x.id === projectId);
    const task = proj?.tasks.find(tk => tk.id === taskId);
    if (!proj || !task) return;
    try {
      await D_app.API.startTimer(proj.id, task.id);
      updateProject(proj.id, p => ({
        ...p, tasks: p.tasks.map(tk => tk.id === task.id ? { ...tk, timerStartedAt: new Date().toISOString() } : tk),
      }));
      setActiveTimer({ taskId: task.id, projectId: proj.id, taskName: task.name, projectName: proj.name, startedAt: Date.now(), baseElapsed: task.elapsedSeconds || 0 });
    } catch (e) { toast("Error al iniciar timer", "error"); }
  }, [activeTimer, projects, toast, t.demoData]);

  const onPauseTimer = useCallbackApp(async () => {
    if (!activeTimer) return;
    try {
      await D_app.API.pauseTimer(activeTimer.projectId, activeTimer.taskId);
      const elapsed = activeTimer.baseElapsed + Math.floor((Date.now() - activeTimer.startedAt) / 1000);
      const elapsedHours = Math.round(elapsed / 3600 * 100) / 100;
      const todayISO = new Date().toISOString().slice(0, 10);
      updateProject(activeTimer.projectId, p => {
        const newWH = elapsed >= 60 ? [...(p.workHours || []), {
          id: "timer-" + Date.now(), hours: elapsedHours,
          date: todayISO, desc: `⏱ Timer: ${activeTimer.taskName}`,
          createdAt: new Date().toISOString(),
        }] : (p.workHours || []);
        return {
          ...p,
          tasks: p.tasks.map(tk => tk.id === activeTimer.taskId ? { ...tk, elapsedSeconds: elapsed, timerStartedAt: null } : tk),
          actualHours: elapsed >= 60 ? Math.round((p.actualHours + elapsedHours) * 100) / 100 : p.actualHours,
          workHours: newWH,
          history: elapsed >= 60 ? [{ time: "ahora", text: `+${elapsedHours}h (Timer: ${activeTimer.taskName})`, type: "hours" }, ...(p.history || [])] : (p.history || []),
        };
      });
      toast(`Timer pausado — ${formatTimer(elapsed)}${elapsed >= 60 ? ` (${elapsedHours}h sumadas al proyecto)` : ""}`);
      setActiveTimer(null);
    } catch (e) { toast("Error al pausar timer", "error"); }
  }, [activeTimer, toast]);

  // ----- Move project (kanban drag)
  const onMoveProject = useCallbackApp(async (projectId, newState) => {
    const proj = projects.find(x => x.id === projectId);
    if (!proj || proj.state === newState) return;
    exec("CHANGE_STATE", { projectId, newState });
  }, [projects, exec]);

  // ----- Login
  if (!logged) {
    return (
      <div data-theme={theme} style={{ height: "100vh" }}>
        <Login onLogin={userInfo => { setCurrentUser(userInfo || null); setLogged(true); }} />
      </div>
    );
  }

  // ----- Main shell
  const chatPanel = (
    <window.MAESTRO_CHAT.ChatPanel
      messages={messages}
      onSend={onSend}
      onConfirm={onConfirm}
      onOpenProject={setOpenProjectId}
    />
  );

  return (
    <div className="app-shell">
      <Header
        view={view}
        setView={setView}
        theme={theme}
        setTheme={setTheme}
        onLogout={() => { D_app.clearToken(); setLogged(false); setCurrentUser(null); }}
        alertCount={alertCount}
        projects={projects}
        onOpenProject={setOpenProjectId}
      />

      <div className="app-body" style={{ display: "grid", gridTemplateColumns: "1fr 380px", height: "100%", minHeight: 0 }}>
        <div className="section-host">
          {openDetailId && (() => {
            const detailProject = projects.find(p => p.id === openDetailId);
            if (!detailProject) return null;
            return (
              <ProjectDetail
                project={detailProject}
                onClose={() => { setOpenDetailId(null); }}
                onToggleTask={onToggleTask}
                onResolveBlocker={(projectId, blockerId) => exec("RESOLVE_BLOCKER", { projectId, blockerId })}
                onAddBlocker={(projectId, desc, tipo) => exec("ADD_BLOCKER", { projectId, desc, tipo })}
                onChangeState={(projectId, newState) => exec("CHANGE_STATE", { projectId, newState })}
                onEditProject={(projectId, updates) => exec("EDIT_PROJECT", { projectId, updates })}
                onDeleteProject={async (projectId) => { await exec("DELETE_PROJECT", { projectId }); setOpenDetailId(null); setOpenProjectId(null); }}
                onAddHours={(projectId, hours, description) => exec("ADD_HOURS", { projectId, hours, description })}
                onAddNote={(projectId, contenido, tipo) => exec("ADD_NOTE", { projectId, contenido, tipo })}
                onArchiveProject={(projectId, currentArchived) => exec("ARCHIVE_PROJECT", { projectId, currentArchived })}
                onDuplicateProject={(projectId) => { exec("DUPLICATE_PROJECT", { projectId }); setOpenDetailId(null); }}
                onUpdateTaskSubtasks={(projectId, taskId, subtareas) => exec("UPDATE_TASK_SUBTASKS", { projectId, taskId, subtareas })}
                onAddTask={(payload) => exec("ADD_TASK", payload)}
                onUploadTaskPrepFile={async (projectId, taskId, file) => {
                  try {
                    const updated = await D_app.API.uploadTaskPrepFile(projectId, taskId, file);
                    updateProject(projectId, p => ({
                      ...p, tasks: p.tasks.map(t => t.id === taskId ? { ...t, meetingPrepUrl: updated.meeting_prep_url, meetingPrepFilename: updated.meeting_prep_filename } : t),
                    }));
                    toast("Archivo subido");
                  } catch (err) { toast("Error al subir archivo: " + err.message, "error"); }
                }}
                activeTimer={activeTimer}
                timerDisplaySeconds={timerDisplaySeconds}
                onStartTimer={onStartTimer}
                onPauseTimer={onPauseTimer}
                onUploadStructureImage={async (projectId, file) => {
                  try {
                    const updated = await D_app.API.uploadStructureImage(projectId, file);
                    updateProject(projectId, p => ({ ...p, structureImageUrl: updated.structure_image_url || null }));
                    toast("Imagen subida");
                    return updated;
                  } catch (err) {
                    toast("Error al subir imagen: " + err.message, "error");
                    throw err;
                  }
                }}
              />
            );
          })()}
          {!openDetailId && loading && !t.demoData ? (
            <div style={{ padding: 60, textAlign: "center", color: "var(--fg-muted)" }}>
              Cargando proyectos…
            </div>
          ) : !openDetailId && (
            <>
              {view === "inicio" && (
                <HomeSection
                  projects={projects}
                  onOpenProject={setOpenProjectId}
                  onToggleTask={onToggleTask}
                  onJumpView={setView}
                  todayHours={todaySummary.todayHours}
                  tasksDone={todaySummary.tasksDone}
                  projectsTouched={todaySummary.projectsTouched}
                />
              )}
              {view === "proyectos" && (
                <ProjectsSection
                  projects={projects}
                  kanbanView={kanbanView}
                  setKanbanView={setKanbanView}
                  onOpenProject={setOpenProjectId}
                  onMoveProject={onMoveProject}
                  onAddProject={(payload) => exec("ADD_PROJECT", payload)}
                />
              )}
              {view === "tareas" && (
                <TareasSection
                  projects={projects}
                  onOpenProject={setOpenProjectId}
                  onToggleTask={onToggleTask}
                  onAddTask={(payload) => exec("ADD_TASK", payload)}
                />
              )}
              {view === "calendario" && (
                <CalendarioSection projects={projects} onOpenProject={setOpenProjectId} onSyncCalendar={onSyncCalendar} />
              )}
              {view === "stats" && (
                <StatsSection projects={projects} onOpenProject={setOpenProjectId} onRequestInsights={onRequestInsights} />
              )}
              {view === "asistente" && (
                <AsistenteSection
                  projects={projects}
                  messages={messages}
                  onSend={onSend}
                  onConfirm={onConfirm}
                  onOpenProject={setOpenProjectId}
                  sessions={chatSessions}
                  currentSessionId={currentSessionId}
                  onLoadSession={async (sessionId) => {
                    try {
                      const session = await D_app.API.apiFetch(`/chat/sessions/${sessionId}`);
                      const msgs = typeof session.messages === "string" ? JSON.parse(session.messages) : (session.messages || []);
                      const hist = typeof session.api_history === "string" ? JSON.parse(session.api_history) : (session.api_history || []);
                      setMessages(msgs.length ? msgs : D_app.INITIAL_CHAT.map(m => ({ ...m, id: m.id || `m-${Math.random()}` })));
                      setConversationHistory(hist);
                      setCurrentSessionId(sessionId);
                    } catch { }
                  }}
                  onDeleteSession={(sessionId) => {
                    D_app.API.apiFetch(`/chat/sessions/${sessionId}`, { method: "DELETE" }).catch(() => {});
                    setChatSessions(prev => prev.filter(s => s.id !== sessionId));
                    if (currentSessionId === sessionId) {
                      setMessages(D_app.INITIAL_CHAT.map(m => ({ ...m, id: m.id || `m-${Math.random()}` })));
                      setConversationHistory([]);
                      setCurrentSessionId(null);
                    }
                  }}
                  onNewConversation={() => {
                    setMessages(D_app.INITIAL_CHAT.map(m => ({ ...m, id: m.id || `m-${Math.random()}` })));
                    setConversationHistory([]);
                    setCurrentSessionId(null);
                  }}
                />
              )}
              {view === "config" && (
                <ConfigSection
                  theme={theme}
                  setTheme={setTheme}
                  tweaks={t}
                  setTweak={setTweak}
                  onLogout={() => { D_app.clearToken(); setLogged(false); setCurrentUser(null); }}
                  projects={projects}
                />
              )}
            </>
          )}
        </div>

        {/* Chat siempre visible (excepto en vista asistente o cuando el detalle está abierto) */}
        {view !== "asistente" && !openDetailId && chatPanel}
      </div>

      {/* Project drawer */}
      {openProjectId && (
        <Drawer
          project={projects.find(p => p.id === openProjectId)}
          onClose={() => setOpenProjectId(null)}
          onToggleTask={onToggleTask}
          onResolveBlocker={(projectId, blockerId) =>
            exec("RESOLVE_BLOCKER", { projectId, blockerId })
          }
          onChangeState={(projectId, newState) =>
            exec("CHANGE_STATE", { projectId, newState })
          }
          onEditProject={(projectId, updates) =>
            exec("EDIT_PROJECT", { projectId, updates })
          }
          onDeleteProject={async (projectId) => {
            await exec("DELETE_PROJECT", { projectId });
          }}
          onAddHours={(projectId, hours, description) =>
            exec("ADD_HOURS", { projectId, hours, description })
          }
          onAddNote={(projectId, contenido, tipo) =>
            exec("ADD_NOTE", { projectId, contenido, tipo })
          }
          onArchiveProject={(projectId, currentArchived) => exec("ARCHIVE_PROJECT", { projectId, currentArchived })}
          onDuplicateProject={(projectId) => { exec("DUPLICATE_PROJECT", { projectId }); setOpenProjectId(null); }}
          onOpenDetail={handleOpenDetail}
        />
      )}

      {/* Floating timer bar */}
      {activeTimer && (
        <div style={{
          position: "fixed", bottom: 24, left: "50%", transform: "translateX(-50%)",
          background: "var(--bg-surface)", border: "1px solid var(--border)",
          borderLeft: "3px solid var(--accent)", borderRadius: "var(--r-md)",
          boxShadow: "var(--shadow-md)", padding: "10px 20px",
          display: "flex", alignItems: "center", gap: 16,
          zIndex: 9997, minWidth: 340, maxWidth: 580, fontSize: 13,
        }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent)", animation: "pulse 1.5s ease-in-out infinite" }} />
          <span style={{ fontFamily: "monospace", fontWeight: 700, color: "var(--accent)", fontSize: 17, minWidth: 64 }}>
            {formatTimer(timerDisplaySeconds)}
          </span>
          <div style={{ flex: 1, overflow: "hidden" }}>
            <div style={{ fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", fontSize: 13 }}>{activeTimer.taskName}</div>
            <div style={{ fontSize: 11, color: "var(--fg-muted)", marginTop: 1 }}>{activeTimer.projectName}</div>
          </div>
          <button className="btn btn-ghost" style={{ height: 30, fontSize: 12, flexShrink: 0 }} onClick={onPauseTimer}>
            ⏸ Pausar
          </button>
        </div>
      )}

      {/* Toasts */}
      <div style={{ position: "fixed", bottom: 24, right: 24, display: "flex", flexDirection: "column", gap: 8, zIndex: 9999, pointerEvents: "none" }}>
        {toasts.map(toast => (
          <div key={toast.id} className="toast" data-kind={toast.kind || "success"}>
            {toast.text}
          </div>
        ))}
      </div>

      <TweaksPanel />
    </div>
  );
}

const rootEl = document.getElementById("root");
const root = ReactDOM.createRoot(rootEl);
root.render(<App />);
