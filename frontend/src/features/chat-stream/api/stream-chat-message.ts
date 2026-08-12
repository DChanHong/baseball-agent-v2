import { z } from "zod";
import type { ToolResultName } from "@/entities/tool-result/model/types";
import { API_BASE_URL, fetchWithAuthRefresh } from "@/features/auth/api/auth-api";

export type ChatStreamRequest = {
  guestId: string;
  conversationId: string | null;
  message: string;
};

export type ChatStreamMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sequenceNo: number;
  createdAt: string;
};

export type ChatStreamEvent =
  | {
      type: "conversation.created";
      conversationId: string;
      created: boolean;
    }
  | {
      type: "message.created";
      message: ChatStreamMessage;
    }
  | {
      type: "tool.started";
      toolCallId: string;
      name: ToolResultName;
      input: Record<string, unknown>;
    }
  | {
      type: "tool.completed";
      toolCallId: string;
      name: ToolResultName;
      input: Record<string, unknown>;
      result: Record<string, unknown>;
    }
  | {
      type: "tool.failed";
      toolCallId: string;
      name: ToolResultName;
      input: Record<string, unknown>;
      error: {
        code: string;
        message: string;
      };
    }
  | {
      type: "assistant.delta";
      messageId: string;
      delta: string;
    }
  | {
      type: "assistant.completed";
      messageId: string;
      content: string;
      sources: Record<string, unknown>[];
      limitations: string[];
    }
  | {
      type: "conversation.updated";
      conversation: {
        id: string;
        title: string | null;
        lastMessageAt: string | null;
      };
    }
  | {
      type: "stream.failed";
      error: {
        code: string;
        message: string;
      };
    }
  | {
      type: "done";
      conversationId: string;
    };

const toolNameSchema = z.enum([
  "find_kbo_game",
  "get_stadium_info",
  "get_weather_context",
  "search_stadium_guide",
  "search_ticketing_guide",
  "search_baseball_knowledge",
]);

const jsonObjectSchema = z.record(z.string(), z.unknown());

const streamMessageSchema = z
  .object({
    id: z.string().min(1),
    role: z.enum(["user", "assistant"]),
    content: z.string(),
    sequence_no: z.number(),
    created_at: z.string(),
  })
  .transform((message): ChatStreamMessage => ({
    id: message.id,
    role: message.role,
    content: message.content,
    sequenceNo: message.sequence_no,
    createdAt: message.created_at,
  }));

const streamErrorSchema = z.object({
  code: z.string().min(1),
  message: z.string().min(1),
});

const eventSchemas = {
  "conversation.created": z
    .object({
      conversation_id: z.string().min(1),
      created: z.boolean(),
    })
    .transform(
      (event): ChatStreamEvent => ({
        type: "conversation.created",
        conversationId: event.conversation_id,
        created: event.created,
      }),
    ),
  "message.created": z
    .object({
      message: streamMessageSchema,
    })
    .transform(
      (event): ChatStreamEvent => ({
        type: "message.created",
        message: event.message,
      }),
    ),
  "tool.started": z
    .object({
      tool_call_id: z.string().min(1),
      name: toolNameSchema,
      input: jsonObjectSchema,
    })
    .transform(
      (event): ChatStreamEvent => ({
        type: "tool.started",
        toolCallId: event.tool_call_id,
        name: event.name,
        input: event.input,
      }),
    ),
  "tool.completed": z
    .object({
      tool_call_id: z.string().min(1),
      name: toolNameSchema,
      input: jsonObjectSchema,
      result: jsonObjectSchema,
    })
    .transform(
      (event): ChatStreamEvent => ({
        type: "tool.completed",
        toolCallId: event.tool_call_id,
        name: event.name,
        input: event.input,
        result: event.result,
      }),
    ),
  "tool.failed": z
    .object({
      tool_call_id: z.string().min(1),
      name: toolNameSchema,
      input: jsonObjectSchema,
      error: streamErrorSchema,
    })
    .transform(
      (event): ChatStreamEvent => ({
        type: "tool.failed",
        toolCallId: event.tool_call_id,
        name: event.name,
        input: event.input,
        error: event.error,
      }),
    ),
  "assistant.delta": z
    .object({
      message_id: z.string().min(1),
      delta: z.string(),
    })
    .transform(
      (event): ChatStreamEvent => ({
        type: "assistant.delta",
        messageId: event.message_id,
        delta: event.delta,
      }),
    ),
  "assistant.completed": z
    .object({
      message_id: z.string().min(1),
      content: z.string(),
      sources: z.array(jsonObjectSchema),
      limitations: z.array(z.string()),
    })
    .transform(
      (event): ChatStreamEvent => ({
        type: "assistant.completed",
        messageId: event.message_id,
        content: event.content,
        sources: event.sources,
        limitations: event.limitations,
      }),
    ),
  "conversation.updated": z
    .object({
      conversation: z.object({
        id: z.string().min(1),
        title: z.string().nullable(),
        last_message_at: z.string().nullable(),
      }),
    })
    .transform(
      (event): ChatStreamEvent => ({
        type: "conversation.updated",
        conversation: {
          id: event.conversation.id,
          title: event.conversation.title,
          lastMessageAt: event.conversation.last_message_at,
        },
      }),
    ),
  "stream.failed": z
    .object({
      error: streamErrorSchema,
    })
    .transform(
      (event): ChatStreamEvent => ({
        type: "stream.failed",
        error: event.error,
      }),
    ),
  done: z
    .object({
      conversation_id: z.string().min(1),
    })
    .transform(
      (event): ChatStreamEvent => ({
        type: "done",
        conversationId: event.conversation_id,
      }),
    ),
} as const;

type KnownEventName = keyof typeof eventSchemas;

export async function* streamChatMessage(
  request: ChatStreamRequest,
  signal?: AbortSignal,
): AsyncGenerator<ChatStreamEvent> {
  const response = await fetchWithAuthRefresh(`${API_BASE_URL}/api/v1/chat`, {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify({
      guest_id: request.guestId,
      conversation_id: request.conversationId,
      message: request.message,
    }),
    signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`채팅 요청에 실패했습니다. (${response.status})`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() ?? "";

      for (const block of blocks) {
        const event = parseSseBlock(block);

        if (event) {
          yield event;
        }
      }
    }

    buffer += decoder.decode();

    if (buffer.trim()) {
      const event = parseSseBlock(buffer);

      if (event) {
        yield event;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function parseSseBlock(block: string): ChatStreamEvent | null {
  let eventName: string | null = null;
  const dataLines: string[] = [];

  for (const rawLine of block.split(/\r?\n/)) {
    const line = rawLine.trimEnd();

    if (!line || line.startsWith(":")) {
      continue;
    }

    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
      continue;
    }

    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (!eventName || !isKnownEventName(eventName) || dataLines.length === 0) {
    return null;
  }

  const payload = JSON.parse(dataLines.join("\n")) as unknown;
  return eventSchemas[eventName].parse(payload);
}

function isKnownEventName(eventName: string): eventName is KnownEventName {
  return eventName in eventSchemas;
}
