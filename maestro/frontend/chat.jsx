// =====================================================================
// MAESTRO — Chat panel (glassmorphism, agent reply, confirmations)
// =====================================================================
const { useState: useState_chat, useEffect: useEffect_chat, useRef: useRef_chat } = React;
const D_chat = window.MAESTRO_DATA;
const I_chat = window.MAESTRO_ICONS;

function MsgBlock({ block }) {
  if (!block) return null;
  return (
    <div className="msg-block">
      <div className="msg-block-title">{block.title}</div>
      <div className="msg-kv">
        {block.items.map(([k, v], i) => (
          <React.Fragment key={i}>
            <span className="k">{k}</span>
            <span>{v}</span>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

function RiskList({ risks, onOpenProject }) {
  return (
    <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
      {risks.map((r, i) => (
        <div key={r.id} className="msg-block" style={{ borderLeft: `3px solid var(--${r.severity})` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
            <span style={{ color: `var(--${r.severity})` }}>{r.severity === "danger" ? I_chat.blocked(13) : I_chat.alert(13)}</span>
            <span
              className="msg-proj-link"
              onClick={() => onOpenProject(r.id)}
            >{r.name}</span>
          </div>
          <div style={{ fontSize: 12, color: "var(--fg-muted)", lineHeight: 1.4 }}>{r.reason}</div>
        </div>
      ))}
    </div>
  );
}

function ChatMessage({ msg, onConfirm, onOpenProject }) {
  const isUser = msg.role === "user";
  return (
    <div className={`msg ${isUser ? "user" : "agent"}`}>
      <div className="msg-avatar">{isUser ? "A" : "M"}</div>
      <div className="msg-bubble">
        {msg.thinking ? (
          <div className="typing-dots"><span /><span /><span /></div>
        ) : (
          <>
            <div style={{ whiteSpace: "pre-wrap" }}>
              {msg.text}
              {msg.inlineProj && (
                <span
                  className="msg-proj-link"
                  onClick={() => onOpenProject(msg.inlineProj.id)}
                >{msg.inlineProj.name}</span>
              )}
              {msg.textAfter}
            </div>
            {msg.block && <MsgBlock block={msg.block} />}
            {msg.risks && <RiskList risks={msg.risks} onOpenProject={onOpenProject} />}
            {msg.followup && <div style={{ marginTop: 8, color: "var(--fg-muted)", fontSize: 12.5 }}>{msg.followup}</div>}
            {msg.confirm && !msg.resolved && (
              <div className="msg-confirm">
                <button className="btn-confirm-yes" onClick={() => onConfirm(msg.id, true)}>
                  {I_chat.check(14)} Sí, ejecutar
                </button>
                <button className="btn-confirm-no" onClick={() => onConfirm(msg.id, false)}>
                  {I_chat.x(14)} No
                </button>
              </div>
            )}
            {msg.confirm && msg.resolved && (
              <div className="msg-confirm resolved">
                <button className={`btn-confirm-yes ${msg.resolved === "yes" ? "chosen" : ""}`}>
                  {I_chat.check(14)} {msg.resolved === "yes" ? "Confirmado" : "Sí"}
                </button>
                <button className={`btn-confirm-no ${msg.resolved === "no" ? "chosen" : ""}`}>
                  {I_chat.x(14)} {msg.resolved === "no" ? "Cancelado" : "No"}
                </button>
              </div>
            )}
            {!msg.thinking && msg.time && (
              <div style={{ fontSize: 10, color: isUser ? "oklch(1 0 0 / 0.7)" : "var(--fg-subtle)", marginTop: 6, fontFamily: "var(--font-mono)" }}>
                {msg.time}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function ChatPanel({ messages, onSend, onConfirm, onOpenProject }) {
  const [input, setInput] = useState_chat("");
  const scrollRef = useRef_chat(null);
  const taRef = useRef_chat(null);

  useEffect_chat(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }
  }, [messages.length, messages[messages.length - 1]?.thinking]);

  const submit = () => {
    if (!input.trim()) return;
    onSend(input);
    setInput("");
    if (taRef.current) taRef.current.style.height = "20px";
  };

  const onKey = e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const onInputChange = e => {
    setInput(e.target.value);
    if (taRef.current) {
      taRef.current.style.height = "20px";
      taRef.current.style.height = Math.min(taRef.current.scrollHeight, 120) + "px";
    }
  };

  return (
    <aside className="chat-pane">
      <div className="chat-head">
        <div className="chat-id">
          <div className="chat-avatar">{I_chat.sparkles(16)}</div>
          <div>
            <div className="chat-id-name">Asistente</div>
            <div className="chat-id-status">
              <span style={{ width: 6, height: 6, borderRadius: 99, background: "var(--success)" }} />
              Online · respondiendo en ~1s
            </div>
          </div>
        </div>
        <button className="btn btn-ghost btn-icon" title="Opciones">{I_chat.more(14)}</button>
      </div>

      <div className="chat-scroll" ref={scrollRef}>
        {messages.map(m => (
          <ChatMessage key={m.id} msg={m} onConfirm={onConfirm} onOpenProject={onOpenProject} />
        ))}
      </div>

      <div className="quick-prompts">
        {D_chat.QUICK_PROMPTS.map(q => (
          <button key={q} onClick={() => onSend(q)}>{q}</button>
        ))}
      </div>

      <div className="chat-composer">
        <div className="composer-shell">
          <textarea
            ref={taRef}
            value={input}
            onChange={onInputChange}
            onKeyDown={onKey}
            rows={1}
            placeholder="Escribí algo… (ej: «agregá 2h a APODERAR»)"
          />
          <button className="send-btn" onClick={submit} disabled={!input.trim()}>
            {I_chat.send(15)}
          </button>
        </div>
        <div style={{ marginTop: 8, fontSize: 10.5, color: "var(--fg-subtle)", display: "flex", justifyContent: "space-between", fontFamily: "var(--font-mono)" }}>
          <span>Enter para enviar · Shift + Enter para nueva línea</span>
          <span>claude-haiku</span>
        </div>
      </div>
    </aside>
  );
}

window.MAESTRO_CHAT = { ChatPanel };
