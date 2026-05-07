"use client";

import { FormEvent, useMemo, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  Building2,
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  Factory,
  FileText,
  Gauge,
  Loader2,
  Send,
  SquareStack,
  Zap,
} from "lucide-react";
import { Badge, Button, Progress, ScrollArea, Separator, Textarea } from "@/components/ui";
import { getInitialLeadState, postLeadTurn } from "@/lib/lead-api";
import { cn } from "@/lib/utils";
import type { LeadSlotKey, LeadState, LeadTurnResponse } from "@/types/lead";

type ChatMessage = {
  id: string;
  role: "assistant" | "user";
  content: string;
};

const slots: Array<{
  key: LeadSlotKey;
  label: string;
  icon: typeof Building2;
}> = [
  { key: "segment", label: "Segment", icon: Factory },
  { key: "usage", label: "Annual usage", icon: Gauge },
  { key: "square_footage", label: "Square footage", icon: SquareStack },
  { key: "provider_contract", label: "Provider / contract", icon: FileText },
  { key: "expiry", label: "Expiry", icon: CalendarClock },
  { key: "building_age", label: "Building age", icon: Building2 },
  { key: "tier_status", label: "Tier / status", icon: Activity },
];

const quickStarts = [
  {
    label: "Paste discovery notes",
    prompt:
      "I have discovery notes for an ABC Energy prospect. Help me extract the qualification fields and ask only for what is missing.",
    icon: ClipboardList,
  },
  {
    label: "Qualify known usage",
    prompt:
      "Qualify an internal prospect where I already know annual usage. Help me capture provider, contract expiry, facility segment, and building details.",
    icon: Gauge,
  },
  {
    label: "Estimate from facility size",
    prompt:
      "Estimate from facility size for an internal lead. I do not have annual usage, but I can provide square footage, segment, and building details.",
    icon: SquareStack,
  },
];

const initialMessages: ChatMessage[] = [
  {
    id: "welcome",
    role: "assistant",
    content:
      "Paste notes from a call, CRM record, spreadsheet row, or prospect research. I will extract the lead details, ask only for missing fields, and prepare the ABC Energy tier recommendation.",
  },
];

export function LeadQualificationAssistant() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string>();
  const [leadState, setLeadState] = useState<LeadState>(getInitialLeadState);
  const [missingFields, setMissingFields] = useState<LeadSlotKey[]>([
    "segment",
    "usage",
    "square_footage",
    "provider_contract",
    "expiry",
    "building_age",
  ]);
  const [isSending, setIsSending] = useState(false);
  const [lastTraceSource, setLastTraceSource] = useState("waiting");

  const completedSlots = useMemo(
    () => slots.filter((slot) => Boolean(readSlot(leadState, slot.key))).length,
    [leadState],
  );
  const progress = Math.round((completedSlots / slots.length) * 100);

  async function sendMessage(message: string) {
    const trimmed = message.trim();
    if (!trimmed || isSending) return;

    const userMessage: ChatMessage = {
      id: createMessageId("user"),
      role: "user",
      content: trimmed,
    };

    setMessages((current) => [...current, userMessage]);
    setInput("");
    setIsSending(true);

    const result = await postLeadTurn({ session_id: sessionId, message: trimmed }, leadState);

    applyLeadTurn(result);
    setIsSending(false);
  }

  function applyLeadTurn(result: LeadTurnResponse) {
    setSessionId(result.session_id);
    setLeadState(result.state);
    setMissingFields(result.missing_fields);
    setLastTraceSource(getTraceSource(result.trace));
    setMessages((current) => [
      ...current,
      {
        id: createMessageId("assistant"),
        role: "assistant",
        content: result.response,
      },
    ]);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(input);
  }

  return (
    <main className="min-h-screen bg-[#f7f8f4] text-[#18201b]">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-4 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-3 border-b border-[#d9ded1] pb-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#254c3a] text-white">
              <Zap className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-[#254c3a]">ABC Energy Solutions</p>
              <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">
                Internal lead qualification workspace
              </h1>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="border-[#b8c6b4] bg-white text-[#254c3a]" variant="outline">
              Sales intake
            </Badge>
            <Badge className="border-[#c7d8e0] bg-[#eef6f8] text-[#28505e]" variant="outline">
              CRA review
            </Badge>
          </div>
        </header>

        <section className="grid min-h-0 flex-1 gap-4 py-4 lg:grid-cols-[minmax(0,1fr)_380px]">
          <div className="flex min-h-[620px] flex-col rounded-lg border border-[#d9ded1] bg-white">
            <div className="border-b border-[#e2e5dd] p-4">
              <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
                <div>
                  <h2 className="text-base font-semibold">Qualification conversation</h2>
                  <p className="mt-1 max-w-2xl text-sm text-[#5f6b62]">
                    Paste prospect notes or enter known account facts. The assistant keeps the
                    internal reviewer focused on the missing fields needed for tiering.
                  </p>
                </div>
                <div className="flex items-center gap-2 text-xs text-[#5f6b62]">
                  <span className="h-2 w-2 rounded-full bg-[#2f6f4e]" />
                  API source: {lastTraceSource}
                </div>
              </div>

              <div className="mt-4 grid gap-2 md:grid-cols-3">
                {quickStarts.map((quickStart) => {
                  const Icon = quickStart.icon;
                  return (
                    <Button
                      className="h-auto justify-start border-[#ccd5c7] px-3 py-3 text-left font-medium"
                      disabled={isSending}
                      key={quickStart.label}
                      onClick={() => void sendMessage(quickStart.prompt)}
                      type="button"
                      variant="outline"
                    >
                      <Icon className="h-4 w-4 text-[#2f6f4e]" />
                      <span className="min-w-0 whitespace-normal">{quickStart.label}</span>
                    </Button>
                  );
                })}
              </div>
            </div>

            <ScrollArea className="min-h-0 flex-1">
              <div className="space-y-4 p-4">
                {messages.map((message) => (
                  <div
                    className={cn(
                      "flex",
                      message.role === "user" ? "justify-end" : "justify-start",
                    )}
                    key={message.id}
                  >
                    <div
                      className={cn(
                        "max-w-[88%] rounded-lg px-4 py-3 text-sm leading-6 shadow-sm sm:max-w-[74%]",
                        message.role === "user"
                          ? "bg-[#254c3a] text-white"
                          : "border border-[#dfe4da] bg-[#f8faf5] text-[#253027]",
                      )}
                    >
                      {message.content}
                    </div>
                  </div>
                ))}
                {isSending && (
                  <div className="flex justify-start">
                    <div className="flex items-center gap-2 rounded-lg border border-[#dfe4da] bg-[#f8faf5] px-4 py-3 text-sm text-[#5f6b62]">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Reviewing qualification fields
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>

            <form className="border-t border-[#e2e5dd] p-4" onSubmit={handleSubmit}>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Textarea
                  className="min-h-12 resize-none border-[#ccd5c7] bg-white text-sm"
                  onChange={(event) => setInput(event.target.value)}
                  placeholder="Example: CRM note says manufacturing facility, 62,000 sq ft, 540,000 kWh annually, contract with Constellation expires October 2026, built in 1998."
                  value={input}
                />
                <Button
                  className="h-12 bg-[#254c3a] px-5 text-white hover:bg-[#1f3f31]"
                  disabled={isSending || input.trim().length === 0}
                  type="submit"
                >
                  <Send className="h-4 w-4" />
                  Send
                </Button>
              </div>
            </form>
          </div>

          <aside className="rounded-lg border border-[#d9ded1] bg-white">
            <div className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold">Lead summary</h2>
                  <p className="mt-1 text-sm text-[#5f6b62]">
                    Internal qualification fields update from the backend state.
                  </p>
                </div>
                <div className="rounded-lg bg-[#eef6f8] p-2 text-[#28505e]">
                  <ArrowUpRight className="h-4 w-4" />
                </div>
              </div>

              <div className="mt-4">
                <div className="mb-2 flex items-center justify-between text-sm">
                  <span className="font-medium">
                    {completedSlots} of {slots.length}
                  </span>
                  <span className="text-[#5f6b62]">{progress}% complete</span>
                </div>
                <Progress className="bg-[#e5ebdf] [&>div]:bg-[#2f6f4e]" value={progress} />
              </div>
            </div>

            <Separator className="bg-[#e2e5dd]" />

            <div className="space-y-3 p-4">
              {slots.map((slot) => {
                const value = readSlot(leadState, slot.key);
                const isMissing = slot.key !== "tier_status" && missingFields.includes(slot.key);
                const Icon = slot.icon;

                return (
                  <div
                    className="rounded-lg border border-[#e2e5dd] bg-[#fbfcf8] p-3"
                    key={slot.key}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-2">
                        <Icon className="h-4 w-4 shrink-0 text-[#2f6f4e]" />
                        <span className="truncate text-sm font-medium">{slot.label}</span>
                      </div>
                      {value && !isMissing ? (
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-[#2f6f4e]" />
                      ) : null}
                    </div>
                    <p
                      className={cn(
                        "mt-2 min-h-5 text-sm",
                        value ? "text-[#253027]" : "text-[#899286]",
                      )}
                    >
                      {value ? String(value) : "Not captured"}
                    </p>
                  </div>
                );
              })}
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}

function readSlot(state: LeadState, key: LeadSlotKey) {
  if (key === "tier_status") {
    return (
      state.slots?.tier_status ??
      toDisplayValue(state.tier_status) ??
      [state.tier, state.status].filter(Boolean).join(": ") ??
      undefined
    );
  }

  return state.slots?.[key] ?? toDisplayValue(state[key]);
}

function toDisplayValue(value: unknown) {
  if (value === null || value === undefined || value === "") return undefined;
  if (typeof value === "string" || typeof value === "number") return value;
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return undefined;
}

function getTraceSource(trace: unknown) {
  if (trace && typeof trace === "object" && "source" in trace && typeof trace.source === "string") {
    return trace.source;
  }

  return "backend";
}

function createMessageId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  return `${prefix}-${Date.now()}`;
}
