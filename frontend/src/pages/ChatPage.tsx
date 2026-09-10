/* Creado por Aldo Garcia. */
/**
 * Pantalla principal de chat.
 *
 * Punto importante del diseno: `Matrix` y `MatrixR1` ven **exactamente la misma
 * interfaz**. No hay ninguna opcion oculta por rol. La diferencia de informacion
 * proviene unicamente del backend y sus politicas; ocultar un boton nunca es un
 * control de seguridad.
 */

import { useCallback, useEffect, useState, useRef } from "react";

import { Composer } from "../components/Composer";
import { Icon } from "../components/Icon";
import { MessageList, type DisplayMessage } from "../components/MessageList";
import { QuickActions } from "../components/QuickActions";
import { Sidebar } from "../components/Sidebar";
import { ThemeControl } from "../components/ThemeControl";
import { TracePanel, type ExecutionTrace } from "../components/TracePanel";
import {
  api,
  ApiError,
  type ConversationSummary,
  type DocumentStatus,
  type Me,
} from "../services/api";

type Props = {
  me: Me;
  onLogout: () => void | Promise<void>;
};

/** Iniciales para el avatar de identidad. Nunca mas de dos letras. */
function initials(displayName: string): string {
  const parts = displayName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toLocaleUpperCase("es");
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toLocaleUpperCase("es");
}

export function ChatPage({ me, onLogout }: Props): JSX.Element {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [attachments, setAttachments] = useState<DocumentStatus[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [trace, setTrace] = useState<ExecutionTrace | null>(null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [beforeSeq, setBeforeSeq] = useState<number | null>(null);
  const selected = useRef<string | null>(null);
  const navigation = useRef(0);
  const conversationListRequest = useRef(0);
  const mounted = useRef(false);
  const readController = useRef<AbortController | null>(null);
  const sending = useRef(false);
  const uploadingRef = useRef(false);
  const activeRequest = useRef<string | null>(null);
  const uncertain = useRef(new Map<string, string>());

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      navigation.current += 1;
      conversationListRequest.current += 1;
      readController.current?.abort();
    };
  }, []);

  const describeError = useCallback((caught: unknown): string => {
    if (caught instanceof ApiError) {
      return caught.requestId
        ? `${caught.message} (referencia: ${caught.requestId})`
        : caught.message;
    }
    return "No fue posible completar la operacion.";
  }, []);

  const refreshConversations = useCallback(async () => {
    const ticket = ++conversationListRequest.current;
    try {
      const result = await api.listConversations();
      if (mounted.current && ticket === conversationListRequest.current) setConversations(result);
    } catch (caught) {
      if (mounted.current && ticket === conversationListRequest.current) setError(describeError(caught));
    }
  }, [describeError]);

  useEffect(() => {
    void refreshConversations();
  }, [refreshConversations]);

  const openConversation = useCallback(
    async (id: string) => {
      const ticket = ++navigation.current;
      selected.current = id;
      setActiveId(id);
      setMessages([]);
      setAttachments([]);
      setTrace(null);
      setBeforeSeq(null);
      setLoading(true);
      setError(null);
      setSidebarOpen(false);
      readController.current?.abort();
      readController.current = new AbortController();
      try {
        const detail = await api.getConversation(id, readController.current.signal);
        if (ticket !== navigation.current) return;
        setBeforeSeq(detail.next_before_seq ?? null);
        setAttachments(detail.attachments);
        // La traza corresponde exclusivamente a la ultima respuesta recibida
        // en la conversacion activa. No se reutiliza metadata de otra sesion.
        setTrace(null);
        setMessages(
          detail.messages.map((message) => ({
            id: message.id,
            role: message.role,
            content: message.content,
            // El detalle guarda los source_id citados; la etiqueta legible se
            // reconstruye a partir del propio identificador.
            sources: message.sources.map((source) => ({
              source_id: source.source_id,
              category: source.source_id.split("/")[0] ?? "",
              filename: source.source_id.split("/").slice(1).join("/"),
              section: "",
              page_or_sheet: "",
              score: 0,
              label: source.source_id,
              scope: "corporate",
            })),
          })),
        );
      } catch (caught) {
        if (ticket === navigation.current && !(caught instanceof DOMException && caught.name === "AbortError")) {
          setError(describeError(caught));
        }
      } finally {
        if (ticket === navigation.current) setLoading(false);
      }
    },
    [describeError],
  );

  const startConversation = useCallback(async () => {
    const ticket = ++navigation.current;
    setError(null);
    setSidebarOpen(false);
    readController.current?.abort();
    setLoading(true);
    try {
      const created = await api.createConversation();
      if (ticket !== navigation.current) return;
      selected.current = created.id;
      setActiveId(created.id);
      setBeforeSeq(null);
      setMessages([]);
      setAttachments([]);
      setTrace(null);
      await refreshConversations();
    } catch (caught) {
      if (ticket === navigation.current) setError(describeError(caught));
    } finally {
      if (ticket === navigation.current) setLoading(false);
    }
  }, [describeError, refreshConversations]);

  const removeConversation = useCallback(
    async (id: string) => {
      try {
        await api.deleteConversation(id);
        if (id === selected.current) {
          navigation.current += 1;
          selected.current = null;
          setActiveId(null);
          setLoading(false);
          setBeforeSeq(null);
          readController.current?.abort();
          setMessages([]);
          setAttachments([]);
          setTrace(null);
        }
        await refreshConversations();
      } catch (caught) {
        setError(describeError(caught));
      }
    },
    [describeError, refreshConversations],
  );

  const sendMessage = useCallback(
    async (text: string): Promise<boolean> => {
      if (sending.current || uploadingRef.current || loading) return false;
      sending.current = true;
      const destination = selected.current;
      const ticket = navigation.current;
      // Cada envio incierto conserva su identificador incluso si se consulta
      // otra conversacion o se cambia el borrador antes de volver a intentarlo.
      const requestKey = JSON.stringify([destination, text]);
      const previous = uncertain.current.get(requestKey);
      const requestId = previous ?? crypto.randomUUID();
      activeRequest.current = requestId;
      uncertain.current.set(requestKey, requestId);
      setError(null);
      setPending(true);
      try {
        let reply;
        if (previous) {
          try {
            const status = await api.chatStatus(requestId);
            if (status.status === "running") {
              throw new Error("La solicitud sigue procesandose. Espere y consulte de nuevo.");
            }
            if (status.status === "completed") reply = status.response;
            else { uncertain.current.delete(requestKey); throw new Error("La solicitud termino sin respuesta. Puede volver a enviarla."); }
          } catch (caught) {
            if (!(caught instanceof ApiError && caught.status === 404)) throw caught;
          }
        }
        reply ??= await api.chat(text, destination, requestId);
        uncertain.current.delete(requestKey);
        // La respuesta queda almacenada por el servidor en su conversacion.
        // Solo la presenta si sigue seleccionada; nunca cambia la navegacion.
        if (mounted.current && selected.current === destination && destination
            && (navigation.current !== ticket || previous)) {
          // Al regresar a A durante su respuesta, el historial abierto puede
          // preceder a la persistencia. Se reconcilia A sin seleccionar otra.
          await openConversation(destination);
        } else if (navigation.current === ticket && selected.current === destination) {
          selected.current = reply.conversation_id;
          setActiveId(reply.conversation_id);
          setMessages((current) => [...current,
            { id: `user-${requestId}`, role: "user", content: text, sources: [] },
            { id: reply.message_id, role: "assistant", content: reply.answer, sources: reply.sources },
          ]);
          setTrace({ conversationId: reply.conversation_id, intent: reply.intent,
                     grounded: reply.grounded, latencyMs: reply.latency_ms, sources: reply.sources });
        }
        setDrafts((current) => {
          const key = destination ?? "new";
          if ((current[key] ?? "").trim() === text) return { ...current, [key]: "" };
          // Un acceso rapido envia su propia pregunta: conserva el borrador
          // del usuario, tambien si el servidor acaba de crear la conversacion.
          if (destination === null && current.new) {
            return { ...current, new: "", [reply.conversation_id]: current.new };
          }
          return current;
        });
        if (mounted.current) await refreshConversations();
        return true;
      } catch (caught) {
        if (navigation.current === ticket) {
          setError(caught instanceof Error && !(caught instanceof ApiError) ? caught.message : describeError(caught));
        }
        return false;
      } finally {
        sending.current = false;
        activeRequest.current = null;
        setPending(false);
      }
    },
    [describeError, refreshConversations, loading, openConversation],
  );

  const uploadFiles = useCallback(
    async (files: File[]) => {
      if (sending.current || uploadingRef.current || loading || !files.length) return;
      uploadingRef.current = true;
      setUploading(true);
      setError(null);
      const ticket = navigation.current;
      let conversationId = selected.current;
      const placeholders: DocumentStatus[] = files.map((file) => ({
        id: crypto.randomUUID(), filename: file.name, status: "uploading", chunk_count: 0,
        scope: "conversation", category: null, error_message: null,
      }));
      setAttachments((current) => [...current, ...placeholders]);
      try {
        if (!conversationId) {
          const created = await api.createConversation();
          conversationId = created.id;
          if (navigation.current === ticket) {
            selected.current = created.id;
            setActiveId(created.id);
            setTrace(null);
          }
        }
        const result = await api.uploadAttachments(conversationId, files);
        if (navigation.current === ticket && selected.current === conversationId) {
          setAttachments((current) => [...current.filter((item) => !placeholders.some((p) => p.id === item.id)), ...result.documents]);
        }
        await refreshConversations();
      } catch (caught) {
        if (navigation.current === ticket) {
          setError(describeError(caught));
          setAttachments((current) => current.map((item) => placeholders.some((p) => p.id === item.id)
            ? { ...item, status: "failed", error_message: describeError(caught) } : item));
        }
      } finally {
        uploadingRef.current = false;
        setUploading(false);
      }
    },
    [describeError, refreshConversations, loading],
  );

  async function loadOlder(): Promise<void> {
    if (!selected.current || !beforeSeq || loading) return;
    const destination = selected.current;
    const ticket = navigation.current;
    setLoading(true);
    try {
      const detail = await api.getConversation(destination, undefined, beforeSeq);
      if (ticket !== navigation.current) return;
      setBeforeSeq(detail.next_before_seq ?? null);
      setMessages((current) => [...detail.messages.map((m) => ({ id: m.id, role: m.role, content: m.content,
        sources: m.sources.map((source) => ({ ...source, category: "", filename: source.source_id, section: "",
          page_or_sheet: "", score: 0, label: source.source_id, scope: "corporate" })) })), ...current]);
    } catch (caught) { if (ticket === navigation.current) setError(describeError(caught)); }
    finally { if (ticket === navigation.current) setLoading(false); }
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#conversacion">
        Ir a la conversacion
      </a>

      <Sidebar
        open={sidebarOpen}
        conversations={conversations}
        activeId={activeId}
        onSelect={openConversation}
        onCreate={startConversation}
        onDelete={removeConversation}
        onClose={() => setSidebarOpen(false)}
      />

      <header className="app-header">
        <div className="header-title-group">
          <button
            className="icon-button menu-toggle"
            type="button"
            onClick={() => setSidebarOpen((open) => !open)}
            aria-expanded={sidebarOpen}
            aria-controls="conversaciones"
            aria-label="Conversaciones"
            title="Conversaciones"
          >
            <Icon name="menu" />
          </button>
          <div>
            <h1 className="app-title">Recursos Humanos</h1>
            <span className="app-subtitle">Agente especializado de conocimiento</span>
          </div>
        </div>

        <div className="header-actions">
          <span className="local-badge">Matrix RH</span>

          <ThemeControl />

          <button
            className="toggle-button"
            type="button"
            onClick={() => setInspectorOpen((open) => !open)}
            aria-expanded={inspectorOpen}
            aria-label="Mostrar u ocultar trazabilidad"
            title="Trazabilidad"
          >
            <Icon name="panel" size={17} />
            <span className="label">Trazabilidad</span>
          </button>

          <span className="header-divider" aria-hidden="true" />

          <div className="identity">
            <span className="avatar" aria-hidden="true">
              {initials(me.display_name)}
            </span>
            <span className="identity-text">
              <span className="identity-name" data-testid="identity-user">
                {me.display_name}
              </span>
              <span className="identity-meta">
                <span data-testid="identity-source">{me.auth_source}</span>
                <span className="sep" aria-hidden="true">
                  ·
                </span>
                <span data-testid="identity-scope">
                  {me.category_wildcard
                    ? "acceso de negocio ampliado"
                    : `${me.allowed_categories.length} categoria(s)`}
                </span>
              </span>
            </span>
          </div>

          <button className="secondary-button" type="button" onClick={() => void onLogout()}>
            Salir
          </button>
        </div>
      </header>

      {/* El aviso ocupa su propia fila de la rejilla. Antes flotaba sobre la
          conversacion y tapaba el primer mensaje. */}
      {error ? (
        <div className="banner" role="alert" data-testid="error-banner">
          <Icon name="alert" size={17} />
          <p>{error}</p>
          <button type="button" onClick={() => setError(null)} aria-label="Cerrar aviso">
            <Icon name="close" size={16} />
          </button>
        </div>
      ) : null}

      <QuickActions disabled={pending || uploading || loading} onSelect={(prompt) => void sendMessage(prompt)} />

      <main className={`main${inspectorOpen ? " inspector-open" : ""}`}>
        <section className="chat-surface" aria-label="Conversacion con Matrix RH">
          {loading ? <p role="status">Cargando conversacion…</p> : null}
          {uploading ? <p role="status">Cargando y procesando archivos…</p> : null}
          {beforeSeq ? <button type="button" disabled={loading} onClick={() => void loadOlder()}>Cargar mensajes anteriores</button> : null}
          {pending ? <button type="button" onClick={() => {
            if (activeRequest.current) void api.cancelChat(activeRequest.current).then(() => setError("Cancelacion solicitada; se descartara la respuesta pendiente.")).catch((caught) => setError(describeError(caught)));
          }}>Cancelar solicitud</button> : null}
          <MessageList messages={messages} pending={pending} displayName={me.display_name} />

          <Composer
            disabled={pending || uploading || loading}
            attachments={attachments}
            draft={drafts[activeId ?? "new"] ?? ""}
            onDraftChange={(text) => setDrafts((current) => ({ ...current, [activeId ?? "new"]: text }))}
            onSend={sendMessage}
            onUpload={(files) => void uploadFiles(files)}
          />
        </section>

        {inspectorOpen ? (
          <TracePanel trace={trace} onClose={() => setInspectorOpen(false)} />
        ) : null}
      </main>

      {sidebarOpen ? (
        <button
          className="scrim"
          type="button"
          aria-label="Cerrar conversaciones"
          onClick={() => setSidebarOpen(false)}
        />
      ) : null}
    </div>
  );
}
