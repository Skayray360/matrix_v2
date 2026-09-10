/* Creado por Aldo Garcia. */
/** Regresiones unitarias del harness; estos dobles no ejecutan E2E ni modelos. */
import { describe, expect, it, vi } from "vitest";
import type { Page, Request } from "@playwright/test";
import { ask } from "./e2e/helpers";

type Message = { id: string; text: string };
type LocatorDouble = { count?: () => Promise<number>; message?: () => Message };

vi.mock("@playwright/test", () => ({
  expect: (locator: LocatorDouble) => ({
    toBeHidden: async () => undefined,
    toBeVisible: async () => expect(locator.message?.()).toBeDefined(),
    toHaveCount: async (count: number) => expect(await locator.count?.()).toBe(count),
    toHaveAttribute: async (_attribute: string, value: string) => expect(locator.message?.().id).toBe(value),
  }),
}));

function pageDouble({ status = 200, conversation = "A", rendered = true, renderedId = "new" } = {}) {
  const messages: Message[] = [{ id: "previous", text: "Respuesta anterior" }];
  let pendingRequest!: (request: Request) => void;
  const request = {
    method: () => "POST",
    url: () => "http://localhost/api/v1/chat",
    postDataJSON: () => ({ message: "Pregunta nueva", conversation_id: "A", client_request_id: "request-new" }),
    response: async () => ({
      ok: () => status === 200,
      status: () => status,
      json: async () => ({ message_id: "new", conversation_id: conversation, answer: "Respuesta nueva" }),
    }),
  } as unknown as Request;
  const page = {
    waitForRequest: (predicate: (request: Request) => boolean) => new Promise<Request>((resolve) => {
      pendingRequest = (candidate) => { if (predicate(candidate)) resolve(candidate); };
    }),
    getByTestId: (testId: string) => {
      if (testId === "message-assistant") return {
        count: async () => messages.length,
        last: () => ({ message: () => messages.at(-1), innerText: async () => messages.at(-1)?.text }),
      };
      if (testId === "composer-input") return { fill: async () => undefined };
      if (testId === "send-button") return { click: async () => {
        if (rendered && status === 200) messages.push({ id: renderedId, text: "Respuesta nueva" });
        pendingRequest(request);
      } };
      return {};
    },
  } as unknown as Page;
  return page;
}

describe("ask(): correlacion de una respuesta nueva", () => {
  it("rechaza HTTP 503 aunque el mensaje anterior siga visible y pending desaparezca", async () => {
    await expect(ask(pageDouble({ status: 503 }), "Pregunta nueva")).rejects.toThrow("HTTP 503");
  });
  it("rechaza una respuesta de otra conversacion", async () => {
    await expect(ask(pageDouble({ conversation: "B" }), "Pregunta nueva")).rejects.toThrow("otra conversacion");
  });
  it("no acepta el mensaje anterior si el POST 200 nunca se presenta en la interfaz", async () => {
    await expect(ask(pageDouble({ rendered: false }), "Pregunta nueva")).rejects.toThrow();
  });
  it("no acepta un mensaje nuevo distinto del devuelto por el servidor", async () => {
    await expect(ask(pageDouble({ renderedId: "foreign" }), "Pregunta nueva")).rejects.toThrow();
  });
  it("devuelve el mensaje nuevo cuando respuesta y render pertenecen al envio", async () => {
    await expect(ask(pageDouble(), "Pregunta nueva")).resolves.toBe("Respuesta nueva");
  });
});
