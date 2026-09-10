/* Creado por Aldo Garcia. */
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ChatPage } from "../src/pages/ChatPage";
import { api, type ChatReply, type ConversationDetail, type Me } from "../src/services/api";

const me: Me = { user_id: "synthetic", username: "test", display_name: "Test", auth_source: "local_test",
  roles: [], permissions: [], allowed_categories: [], category_wildcard: false, csrf_token: "test" };
const detail = (id: string): ConversationDetail => ({ id, title: `Conversacion ${id}`, created_at: "2026-09-09",
  updated_at: "2026-09-09", messages: [], attachments: [] });
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

beforeEach(() => {
  vi.spyOn(api, "listConversations").mockResolvedValue([detail("A"), detail("B")]);
  vi.spyOn(api, "getConversation").mockImplementation(async (id) => detail(id));
  HTMLElement.prototype.scrollIntoView = vi.fn();
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })));
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("ChatPage concurrencia", () => {
  it("una respuesta tardia de A no se muestra ni cambia la seleccion B", async () => {
    const user = userEvent.setup();
    const response = deferred<ChatReply>();
    vi.spyOn(api, "chat").mockReturnValue(response.promise);
    render(<ChatPage me={me} onLogout={vi.fn()} />);
    await user.click(await screen.findByText("Conversacion A"));
    await waitFor(() => expect(screen.getByTestId("composer-input")).toBeEnabled());
    await user.type(screen.getByTestId("composer-input"), "consulta A{Enter}");
    await waitFor(() => expect(api.chat).toHaveBeenCalled());
    await user.click(screen.getByText("Conversacion B"));
    await act(async () => response.resolve({ conversation_id: "A", message_id: "reply-A", answer: "Respuesta privada A",
      sources: [], intent: "general", grounded: false, latency_ms: 1 }));
    expect(screen.queryByText("Respuesta privada A")).not.toBeInTheDocument();
    expect(screen.getByText("Conversacion B").closest("button")).toHaveAttribute("aria-current", "true");
  });

  it("descarta un historial obsoleto aunque el transporte ignore AbortSignal", async () => {
    const user = userEvent.setup();
    const first = deferred<ConversationDetail>();
    vi.mocked(api.getConversation).mockImplementation((id) => id === "A" ? first.promise : Promise.resolve(detail(id)));
    render(<ChatPage me={me} onLogout={vi.fn()} />);
    await user.click(await screen.findByText("Conversacion A"));
    await user.click(screen.getByText("Conversacion B"));
    await act(async () => first.resolve({ ...detail("A"), messages: [{ id: "old", role: "assistant", content: "Historial A",
      model: null, created_at: "2026-09-09", sources: [] }] }));
    expect(screen.queryByText("Historial A")).not.toBeInTheDocument();
  });

  it("conserva el borrador cuando falla la red", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "chat").mockRejectedValue(new TypeError("Failed to fetch"));
    render(<ChatPage me={me} onLogout={vi.fn()} />);
    await user.click(await screen.findByText("Conversacion A"));
    await waitFor(() => expect(screen.getByTestId("composer-input")).toBeEnabled());
    await user.type(screen.getByTestId("composer-input"), "Mi borrador{Enter}");
    await screen.findByRole("alert");
    expect(screen.getByTestId("composer-input")).toHaveValue("Mi borrador");
  });

  it("recupera el mismo envio incierto de A despues de consultar B", async () => {
    const user = userEvent.setup();
    const replyA: ChatReply = { conversation_id: "A", message_id: "reply-A", answer: "Respuesta recuperada A",
      sources: [], intent: "general", grounded: false, latency_ms: 1 };
    let recovered = false;
    vi.spyOn(api, "chat").mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce({ ...replyA, conversation_id: "B", message_id: "reply-B", answer: "Respuesta B" });
    vi.spyOn(api, "chatStatus").mockImplementation(async () => {
      recovered = true;
      return { status: "completed", conversation_id: "A", response: replyA };
    });
    vi.mocked(api.getConversation).mockImplementation(async (id) => recovered && id === "A"
      ? { ...detail(id), messages: [{ id: "reply-A", role: "assistant", content: replyA.answer,
        model: null, created_at: "2026-09-10", sources: [] }] } : detail(id));
    render(<ChatPage me={me} onLogout={vi.fn()} />);
    await user.click(await screen.findByText("Conversacion A"));
    await waitFor(() => expect(screen.getByTestId("composer-input")).toBeEnabled());
    await user.type(screen.getByTestId("composer-input"), "Consulta A{Enter}");
    await screen.findByRole("alert");
    const requestId = vi.mocked(api.chat).mock.calls[0][2];
    await user.click(screen.getByText("Conversacion B"));
    await waitFor(() => expect(screen.getByTestId("composer-input")).toBeEnabled());
    await user.type(screen.getByTestId("composer-input"), "Consulta B{Enter}");
    await screen.findByText("Respuesta B");
    await user.click(screen.getByText("Conversacion A"));
    await waitFor(() => expect(screen.getByTestId("composer-input")).toBeEnabled());
    expect(screen.getByTestId("composer-input")).toHaveValue("Consulta A");
    await user.click(screen.getByTestId("send-button"));
    await screen.findByText("Respuesta recuperada A");
    expect(api.chatStatus).toHaveBeenCalledWith(requestId);
    expect(api.chat).toHaveBeenCalledTimes(2);
  });

  it("reconcilia la respuesta al regresar a A antes de que termine", async () => {
    const user = userEvent.setup();
    const response = deferred<ChatReply>();
    vi.spyOn(api, "chat").mockReturnValue(response.promise);
    render(<ChatPage me={me} onLogout={vi.fn()} />);
    await user.click(await screen.findByText("Conversacion A"));
    await waitFor(() => expect(screen.getByTestId("composer-input")).toBeEnabled());
    await user.type(screen.getByTestId("composer-input"), "Consulta A{Enter}");
    await user.click(screen.getByText("Conversacion B"));
    await user.click(screen.getByText("Conversacion A"));
    await waitFor(() => expect(api.getConversation).toHaveBeenCalledTimes(3));
    vi.mocked(api.getConversation).mockResolvedValue({ ...detail("A"), messages: [
      { id: "user-A", role: "user", content: "Consulta A", model: null, created_at: "2026-09-10", sources: [] },
      { id: "reply-A", role: "assistant", content: "Respuesta final A", model: null, created_at: "2026-09-10", sources: [] },
    ] });
    await act(async () => response.resolve({ conversation_id: "A", message_id: "reply-A", answer: "Respuesta final A",
      sources: [], intent: "general", grounded: false, latency_ms: 1 }));
    expect(await screen.findByText("Respuesta final A")).toBeInTheDocument();
    expect(screen.getAllByTestId("message-user")).toHaveLength(1);
    expect(screen.getByText("Conversacion A").closest("button")).toHaveAttribute("aria-current", "true");
  });

  it("una lista tardia no restaura una conversacion eliminada", async () => {
    const user = userEvent.setup();
    const staleList = deferred<ConversationDetail[]>();
    vi.mocked(api.listConversations).mockResolvedValueOnce([detail("A"), detail("B")])
      .mockReturnValueOnce(staleList.promise).mockResolvedValueOnce([detail("A")]);
    vi.spyOn(api, "deleteConversation").mockResolvedValue({ ok: true });
    vi.spyOn(api, "chat").mockResolvedValue({ conversation_id: "A", message_id: "reply-A", answer: "Respuesta A",
      sources: [], intent: "general", grounded: false, latency_ms: 1 });
    render(<ChatPage me={me} onLogout={vi.fn()} />);
    await user.click(await screen.findByText("Conversacion A"));
    await waitFor(() => expect(screen.getByTestId("composer-input")).toBeEnabled());
    await user.type(screen.getByTestId("composer-input"), "Consulta A{Enter}");
    await waitFor(() => expect(api.listConversations).toHaveBeenCalledTimes(2));
    await user.click(screen.getByLabelText("Eliminar conversacion Conversacion B"));
    await waitFor(() => expect(screen.queryByText("Conversacion B")).not.toBeInTheDocument());
    await act(async () => staleList.resolve([detail("A"), detail("B")]));
    expect(screen.queryByText("Conversacion B")).not.toBeInTheDocument();
  });

  it("bloquea la consulta mientras el adjunto se carga e indexa", async () => {
    const user = userEvent.setup();
    const upload = deferred<{ documents: [] }>();
    vi.spyOn(api, "uploadAttachments").mockReturnValue(upload.promise);
    vi.spyOn(api, "chat");
    render(<ChatPage me={me} onLogout={vi.fn()} />);
    await user.click(await screen.findByText("Conversacion A"));
    await waitFor(() => expect(screen.getByTestId("composer-input")).toBeEnabled());
    await user.type(screen.getByTestId("composer-input"), "Resume el adjunto");
    await user.upload(screen.getByLabelText("Adjuntar archivos a la conversacion"), new File(["contenido"], "manual.txt"));
    expect(screen.getByTestId("composer-input")).toBeDisabled();
    expect(screen.getByTestId("send-button")).toBeDisabled();
    expect(api.chat).not.toHaveBeenCalled();
    await act(async () => upload.resolve({ documents: [] }));
    expect(screen.getByTestId("composer-input")).toBeEnabled();
    expect(screen.getByTestId("composer-input")).toHaveValue("Resume el adjunto");
  });

  it.each(["A", null])("un acceso rapido conserva el borrador en conversacion %s", async (id) => {
    const user = userEvent.setup();
    vi.spyOn(api, "chat").mockResolvedValue({ conversation_id: "A", message_id: "quick-reply", answer: "Respuesta del tema",
      sources: [], intent: "general", grounded: false, latency_ms: 1 });
    render(<ChatPage me={me} onLogout={vi.fn()} />);
    await screen.findByText("Conversacion A");
    if (id) await user.click(screen.getByText("Conversacion A"));
    await waitFor(() => expect(screen.getByTestId("composer-input")).toBeEnabled());
    await user.type(screen.getByTestId("composer-input"), "Borrador pendiente");
    await user.click(screen.getByTestId("quick-action-general"));
    await screen.findByText("Respuesta del tema");
    expect(screen.getByTestId("composer-input")).toHaveValue("Borrador pendiente");
  });
});
