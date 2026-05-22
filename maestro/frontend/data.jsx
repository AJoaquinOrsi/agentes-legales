// =====================================================================
// MAESTRO — Data layer + API service
// =====================================================================

const _cfg = window.MAESTRO_CONFIG || {};
const API_BASE = _cfg.API_BASE || "http://localhost:8000";
const API_KEY  = _cfg.API_KEY  || "";

// ── State constants ───────────────────────────────────────────────────
const STATES = ["analisis", "desarrollo", "testing", "listo", "produccion"];
const STATE_LABEL = {
  analisis: "En análisis",
  desarrollo: "En desarrollo",
  testing: "Testing",
  listo: "Listo",
  produccion: "Producción",
};
const STATE_LABEL_SHORT = {
  analisis: "Análisis",
  desarrollo: "Desarrollo",
  testing: "Testing",
  listo: "Listo",
  produccion: "Producción",
};

// Map API state values → internal keys
const API_STATE_MAP = {
  "en análisis": "analisis",
  "en desarrollo": "desarrollo",
  "testing": "testing",
  "listo": "listo",
  "producción": "produccion",
};
const INTERNAL_STATE_MAP = {
  analisis: "en análisis",
  desarrollo: "en desarrollo",
  testing: "testing",
  listo: "listo",
  produccion: "producción",
};

// ── Auth token helpers ────────────────────────────────────────────────
const TOKEN_KEY = "maestro_token";

function getToken() { return localStorage.getItem(TOKEN_KEY); }
function setToken(t) { localStorage.setItem(TOKEN_KEY, t); }
function clearToken() { localStorage.removeItem(TOKEN_KEY); }

function getTokenExpiry(token) {
  try {
    const payload = JSON.parse(atob((token || "").split(".")[1] || ""));
    return payload.exp ? payload.exp * 1000 : null; // ms
  } catch { return null; }
}

// ── API helpers ───────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  let res;
  try {
    res = await fetch(API_BASE + path, { ...opts, headers: { ...headers, ...(opts.headers || {}) } });
  } catch (networkErr) {
    // Red caída o servidor apagado — NO borrar token, el usuario sigue "logueado"
    throw new Error("Sin conexión con el servidor. Verificá que esté corriendo.");
  }
  if (res.status === 401) {
    clearToken();
    window.dispatchEvent(new CustomEvent("maestro:unauthorized"));
    throw new Error("Sesión expirada. Volvé a iniciar sesión.");
  }
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err}`);
  }
  if (res.status === 204 || res.headers.get("content-length") === "0") return null;
  return res.json();
}

// Convert API project → UI project shape
function apiProjectToUI(p) {
  const state = API_STATE_MAP[p.estado] || "analisis";

  // Tasks mapped from API
  const tasks = (p.tasks || []).map(t => ({
    id: t.id,
    name: t.descripcion,
    done: t.completada,
    inProgress: !t.completada && !!t.fecha_inicio,
    priority: t.prioridad || "media",
    hours: 0,
    estimated: t.estimated_hours || null,
    fechaInicio: t.fecha_inicio || null,
    fechaVencimiento: t.fecha_vencimiento || null,
    completedAt: t.completed_at || null,
    createdAt: t.created_at,
    subtareas: (() => { try { return t.subtareas_json ? JSON.parse(t.subtareas_json) : []; } catch { return []; } })(),
    elapsedSeconds: t.elapsed_seconds || 0,
    timerStartedAt: t.timer_started_at || null,
    taskType: t.task_type || "task",
    meetingWith: t.meeting_with || null,
    meetingPrepUrl: t.meeting_prep_url || null,
    meetingPrepFilename: t.meeting_prep_filename || null,
    calendarEventId: t.calendar_event_id || null,
  }));

  // Blockers mapped from API
  const blockers = (p.blockers || []).map(b => ({
    id: b.id,
    desc: b.descripcion,
    type: b.tipo,
    resolved: b.resuelto,
    days: b.dias_sin_resolver || 0,
    createdAt: b.created_at,
    resolvedAt: b.resolved_at || null,
  }));

  // Notes mapped from API
  const notes = (p.notes || []).map(n => ({
    id: n.id,
    text: n.contenido,
    type: n.tipo,
    date: new Date(n.created_at).toLocaleString("es-AR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }),
    createdAt: n.created_at,
  }));

  // Work hours mapped from API
  const workHours = (p.work_hours || []).map(wh => ({
    id: wh.id,
    hours: wh.horas,
    date: wh.fecha,
    desc: wh.descripcion || null,
    createdAt: wh.created_at,
  }));

  // Velocity: hours / unique days worked
  const uniqueDays = new Set(workHours.map(wh => wh.date)).size;
  const velocity = uniqueDays > 0 ? Math.round((p.total_hours / uniqueDays) * 10) / 10 : 0;

  // Unified activity feed
  const statusHistory = (p.status_history || []).map(h => ({
    time: new Date(h.changed_at).toLocaleString("es-AR", { day: "2-digit", month: "short" }),
    ts: new Date(h.changed_at).getTime(),
    text: `Cambio de estado: ${h.estado_anterior || "inicio"} -> ${h.estado_nuevo}${h.razon ? ` (${h.razon})` : ""}`,
    type: "state",
    reason: h.razon || null,
    estadoAnterior: h.estado_anterior || null,
    estadoNuevo: h.estado_nuevo,
    changedAt: h.changed_at,
  }));

  const hoursHistory = workHours.map(wh => ({
    time: wh.date,
    ts: new Date(wh.createdAt).getTime(),
    text: `+${wh.hours}h${wh.desc ? `: ${wh.desc}` : ""}`,
    type: "hours",
  }));

  const notesHistory = notes.map(n => ({
    time: n.date,
    ts: new Date(n.createdAt).getTime(),
    text: `Nota (${n.type}): ${n.text.slice(0, 60)}${n.text.length > 60 ? "..." : ""}`,
    type: "note",
  }));

  const history = [...statusHistory, ...hoursHistory, ...notesHistory]
    .sort((a, b) => b.ts - a.ts);

  return {
    id: p.id,
    name: p.nombre,
    clientArea: p.cliente_area || "",
    responsable: p.responsable || null,
    githubUrl: p.github_url || null,
    specsText: p.specs_text || null,
    description: p.descripcion || "Sin descripción.",
    state,
    priority: ["baja","media","alta","critica"].includes(p.prioridad) ? p.prioridad : "media",
    estimatedHours: p.estimated_hours || 10,
    actualHours: p.total_hours || 0,
    daysInState: p.dias_en_estado_actual || 0,
    blocked: p.bloqueado || false,
    archived: p.archived || false,
    deadline: p.deadline || null,
    fechaInicio: p.fecha_inicio || null,
    tags: p.tags ? p.tags.split(",").map(t => t.trim()).filter(Boolean) : [],
    lastUpdate: new Date(p.updated_at).toLocaleString("es-AR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }),
    createdAt: p.created_at,
    velocity,
    tasks,
    blockers,
    notes,
    links: (() => { try { return p.links_json ? JSON.parse(p.links_json) : []; } catch { return []; } })(),
    structureText: p.structure_text || null,
    structureImageUrl: p.structure_image_url || null,
    tarifaHora: p.tarifa_hora || null,
    presupuesto: p.presupuesto || null,
    driveFolderId: p.drive_folder_id || null,
    calendarEventId: p.calendar_event_id || null,
    workHours,
    history,
    statusHistory,
    _raw: p,
  };
}

// ── API service ───────────────────────────────────────────────────────
const API = {
  apiFetch,
  getToken,
  setToken,
  clearToken,

  // Auth
  login: (username, password) =>
    fetch(API_BASE + "/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }).then(async res => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Credenciales incorrectas");
      return data;
    }),
  me: () => apiFetch("/auth/me"),

  // Projects
  getProjects: () => apiFetch("/projects/"),
  createProject: (data) => apiFetch("/projects/", { method: "POST", body: JSON.stringify(data) }),
  changeStatus: (id, estado, razon) =>
    apiFetch(`/projects/${id}/status`, { method: "PATCH", body: JSON.stringify({ estado, razon }) }),

  // Hours
  addHours: (id, horas, descripcion) =>
    apiFetch(`/projects/${id}/hours`, {
      method: "POST",
      body: JSON.stringify({ horas, descripcion, fecha: new Date().toISOString().split("T")[0] }),
    }),

  // Tasks
  createTask: (id, descripcion, prioridad = "media", fecha_inicio = null, fecha_vencimiento = null, task_type = "task", meeting_with = null) =>
    apiFetch(`/projects/${id}/tasks`, { method: "POST", body: JSON.stringify({ descripcion, prioridad, fecha_inicio, fecha_vencimiento, task_type, meeting_with }) }),
  completeTask: (projectId, taskId) =>
    apiFetch(`/projects/${projectId}/tasks/${taskId}/complete`, { method: "PATCH" }),

  // Blockers
  createBlocker: (id, descripcion, tipo = "otro") =>
    apiFetch(`/projects/${id}/blockers`, { method: "POST", body: JSON.stringify({ descripcion, tipo }) }),
  resolveBlocker: (projectId, blockerId) =>
    apiFetch(`/projects/${projectId}/blockers/${blockerId}/resolve`, { method: "PATCH" }),

  // Notes
  addNote: (id, contenido, tipo = "otro") =>
    apiFetch(`/projects/${id}/notes`, { method: "POST", body: JSON.stringify({ contenido, tipo }) }),

  // Chat (real agent)
  chat: (mensaje, conversation_history = []) =>
    apiFetch("/chat/", { method: "POST", body: JSON.stringify({ mensaje, conversation_history }) }),

  // Settings / Integrations
  getIntegrations: () => apiFetch("/settings/integrations"),
  saveIntegrations: (data) =>
    apiFetch("/settings/integrations", { method: "POST", body: JSON.stringify(data) }),
  testService: (service) =>
    apiFetch(`/settings/test/${service}`, { method: "POST" }),
  getGoogleServiceAccountEmail: () =>
    apiFetch("/settings/google-service-account-email"),

  updateProject: (id, updates) =>
    apiFetch(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(updates) }),

  updateTask: (projectId, taskId, updates) =>
    apiFetch(`/projects/${projectId}/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify(updates) }),

  deleteTask: (projectId, taskId) =>
    apiFetch(`/projects/${projectId}/tasks/${taskId}`, { method: "DELETE" }),

  // ── Notificaciones ─────────────────────────────────────────────────────────
  getNotifications: () => apiFetch("/notifications"),
  getNotificationCount: () => apiFetch("/notifications/count"),
  markNotificationRead: (id) => apiFetch(`/notifications/${id}/read`, { method: "POST" }),
  markAllNotificationsRead: () => apiFetch("/notifications/read-all", { method: "POST" }),
  deleteNotification: (id) => apiFetch(`/notifications/${id}`, { method: "DELETE" }),

  startTimer: (projectId, taskId) =>
    apiFetch(`/projects/${projectId}/tasks/${taskId}/timer/start`, { method: "POST" }),
  pauseTimer: (projectId, taskId) =>
    apiFetch(`/projects/${projectId}/tasks/${taskId}/timer/pause`, { method: "POST" }),

  uploadTaskPrepFile: async (projectId, taskId, file) => {
    const token = getToken();
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(API_BASE + `/projects/${projectId}/tasks/${taskId}/prep-file`, {
      method: "POST",
      headers: token ? { "Authorization": `Bearer ${token}` } : {},
      body: formData,
    });
    if (res.status === 401) { clearToken(); window.dispatchEvent(new CustomEvent("maestro:unauthorized")); throw new Error("Sesión expirada."); }
    if (!res.ok) { const err = await res.text(); throw new Error(`Upload ${res.status}: ${err}`); }
    return res.json();
  },

  uploadStructureImage: async (projectId, file) => {
    const token = getToken();
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(API_BASE + `/projects/${projectId}/structure-image`, {
      method: "POST",
      headers: token ? { "Authorization": `Bearer ${token}` } : {},
      body: formData,
    });
    if (res.status === 401) { clearToken(); window.dispatchEvent(new CustomEvent("maestro:unauthorized")); throw new Error("Sesión expirada."); }
    if (!res.ok) { const err = await res.text(); throw new Error(`Upload ${res.status}: ${err}`); }
    return res.json();
  },

  // ── Google ──────────────────────────────────────────────────────────
  googleStatus: () => apiFetch("/google/status"),

  googleCalendarUpcoming: (days = 30) =>
    apiFetch(`/google/calendar/upcoming?days=${days}`),

  googleCalendarSync: (projectId) =>
    apiFetch(`/google/calendar/sync/${projectId}`, { method: "POST" }),

  googleCalendarDeleteEvent: (eventId, projectId) =>
    apiFetch(`/google/calendar/event/${eventId}?project_id=${projectId}`, { method: "DELETE" }),

  googleDriveFolder: (projectId) =>
    apiFetch(`/google/drive/folder/${projectId}`),

  googleDriveFiles: (projectId) =>
    apiFetch(`/google/drive/files/${projectId}`),
};

// ── Client-side helpers (for local parsing without API) ───────────────
function findProject(projects, text) {
  const t = text.toLowerCase();
  for (const p of projects) {
    const n = p.name.toLowerCase();
    if (t.includes(n)) return p;
    const firstWord = n.split(" ")[0];
    if (firstWord.length > 3 && t.includes(firstWord)) return p;
  }
  return null;
}

function parseHours(text) {
  const m = text.match(/([\d.,]+)\s*(?:h|hs|hrs|hora|horas)/i);
  if (!m) return null;
  return parseFloat(m[1].replace(",", "."));
}

function parseState(text) {
  const t = text.toLowerCase();
  if (t.includes("analisis") || t.includes("análisis")) return "analisis";
  if (t.includes("desarrollo") || t.includes("dev")) return "desarrollo";
  if (t.includes("testing") || t.includes("test")) return "testing";
  if (t.includes("listo") || t.includes("ready")) return "listo";
  if (t.includes("produccion") || t.includes("producción") || t.includes("prod")) return "produccion";
  return null;
}

// ── CSV export helper ─────────────────────────────────────────────────
function exportProjectsCSV(projects) {
  const rows = [["ID","Nombre","Cliente","Estado","Prioridad","HorasEst","HorasReal","Deadline","Responsable","Bloqueado","Tags"]];
  projects.forEach(p => {
    rows.push([
      p.id, p.name, p.clientArea, p.state, p.priority,
      p.estimatedHours, p.actualHours, p.deadline || "",
      p.responsable || "", p.blocked ? "SI" : "NO",
      (p.tags || []).join("|"),
    ]);
  });
  const csv = rows.map(r => r.map(v => `"${String(v ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "maestro-proyectos.csv"; a.click();
  URL.revokeObjectURL(url);
}

function exportTasksCSV(projects) {
  const rows = [["Proyecto","Tarea","Prioridad","Completada","HorasEst","Vencimiento"]];
  projects.forEach(p => {
    (p.tasks || []).forEach(t => {
      rows.push([p.name, t.name, t.priority, t.done ? "SI" : "NO", t.estimated || "", t.fechaVencimiento || ""]);
    });
  });
  const csv = rows.map(r => r.map(v => `"${String(v ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "maestro-tareas.csv"; a.click();
  URL.revokeObjectURL(url);
}

// ── Initial / demo data ───────────────────────────────────────────────
const INITIAL_PROJECTS = [];

const DEMO_PROJECTS = [
  {
    id: "apoderar",
    name: "APODERAR",
    description: "Automatización de poderes en portal PJN.",
    state: "desarrollo",
    priority: "alta",
    estimatedHours: 8,
    actualHours: 18,
    daysInState: 5,
    blocked: false,
    deadline: "25 May",
    tags: ["RPA", "Legal"],
    lastUpdate: "hoy 10:00",
    velocity: 3.6,
    tasks: [
      { id: "t1", name: "Mapear flujo del portal PJN", done: true, hours: 4 },
      { id: "t2", name: "Implementar lógica de GWT", done: true, hours: 6 },
      { id: "t3", name: "Manejo de captchas", done: false, hours: 0, estimated: 3 },
    ],
    blockers: [],
    notes: [{ id: "n1", text: "El portal cambia DOM a cada release: usar selectores resilientes.", type: "learning", date: "13 May" }],
    links: [{ label: "Repo", url: "#" }],
    history: [
      { time: "hoy 10:00", text: "Agregaste 2h trabajando en lógica GWT", type: "time" },
      { time: "12 May", text: "Cambio de estado: análisis → desarrollo", type: "state" },
    ],
  },
  {
    id: "arca",
    name: "ARCA Bot",
    description: "Descarga de notificaciones SRT/AFIP a Google Drive.",
    state: "testing",
    priority: "alta",
    estimatedHours: 15,
    actualHours: 22,
    daysInState: 2,
    blocked: false,
    deadline: "22 May",
    tags: ["API", "RPA"],
    lastUpdate: "ayer 18:20",
    velocity: 2.2,
    tasks: [
      { id: "t1", name: "Integrar Claude API para parsing", done: true, hours: 4 },
      { id: "t2", name: "Tests en cuenta sandbox", done: false, hours: 1, estimated: 3 },
    ],
    blockers: [],
    notes: [{ id: "n1", text: "Batch processing es crítico para >500 notificaciones.", type: "learning", date: "11 May" }],
    links: [],
    history: [{ time: "ayer 18:20", text: "Cambio de estado: desarrollo → testing", type: "state" }],
  },
  {
    id: "foliar",
    name: "FOLIAR",
    description: "Foliación automática de documentos legales.",
    state: "desarrollo",
    priority: "media",
    estimatedHours: 12,
    actualHours: 7,
    daysInState: 6,
    blocked: true,
    deadline: "30 May",
    tags: ["RPA", "Legal"],
    lastUpdate: "hace 4 días",
    velocity: 1.2,
    tasks: [
      { id: "t1", name: "POC de pdf-lib", done: true, hours: 3 },
      { id: "t2", name: "Integración con sistema cliente", done: false, hours: 0, estimated: 5 },
    ],
    blockers: [{ id: "b1", desc: "Sin acceso al sistema de foliación del cliente", type: "acceso", createdAt: "11 May", days: 4, resolved: false }],
    notes: [],
    links: [],
    history: [
      { time: "11 May", text: "Bloqueador creado: sin acceso a sistema", type: "blocker" },
      { time: "09 May", text: "Cambio de estado: análisis → desarrollo", type: "state" },
    ],
  },
];

const INITIAL_CHAT = [
  {
    id: "m-welcome",
    role: "agent",
    time: new Date().toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" }),
    text: "¡Hola, Alexis! 👋 Soy MAESTRO, tu asistente de proyectos. Cargando datos desde el servidor…",
  },
];

const DEMO_CHAT = [
  {
    id: "m-welcome",
    role: "agent",
    time: "09:02",
    text: "¡Buen día, Alexis! 👋 Modo demo activo — los datos son de prueba.",
    block: {
      title: "Resumen rápido (demo)",
      items: [
        ["Proyectos activos", "3"],
        ["En riesgo", "2 — FOLIAR · ARCA Bot"],
        ["Tareas pendientes", "4"],
      ],
    },
  },
];

const QUICK_PROMPTS = [
  "¿Cuáles están en riesgo?",
  "Agregá 2h a APODERAR",
  "Pasá ARCA Bot a listo",
  "¿Cuántas horas trabajé hoy?",
];

// ── Agent reply: calls the real backend ──────────────────────────────
// Returns a Promise<msgObject>. App calls this async.
async function buildAgentReply(userText, ctx) {
  try {
    const result = await API.chat(userText, ctx.conversationHistory || []);
    // Store the updated history in ctx so caller can persist it
    ctx._newHistory = result.conversation_history || [];
    ctx._toolsExecuted = result.tool_calls_executed || [];

    return {
      role: "agent",
      text: result.respuesta,
    };
  } catch (err) {
    console.error("Chat API error:", err);
    return {
      role: "agent",
      text: `⚠️ No pude conectarme al servidor. Verificá que el backend esté corriendo en ${API_BASE}.\n\nError: ${err.message}`,
    };
  }
}

window.MAESTRO_DATA = {
  API_BASE,
  STATES,
  STATE_LABEL,
  STATE_LABEL_SHORT,
  INITIAL_PROJECTS,
  INITIAL_CHAT,
  DEMO_PROJECTS,
  DEMO_CHAT,
  QUICK_PROMPTS,
  buildAgentReply,
  findProject,
  API,
  apiProjectToUI,
  INTERNAL_STATE_MAP,
  getToken,
  setToken,
  clearToken,
  getTokenExpiry,
  TOKEN_KEY,
  exportProjectsCSV,
  exportTasksCSV,
};
