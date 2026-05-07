import type {
  BackendLeadState,
  LeadClassification,
  LeadSession,
  LeadSessionsResponse,
  LeadSlotKey,
  LeadState,
  LeadTurnRequest,
  LeadTurnResponse,
} from "@/types/lead";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

const LEAD_ENDPOINT = `${BACKEND_URL}/api/v1/lead/turn`;
const LEAD_SESSIONS_ENDPOINT = `${BACKEND_URL}/api/v1/lead/sessions`;

const REQUIRED_FIELDS: LeadSlotKey[] = [
  "segment",
  "usage",
  "square_footage",
  "provider_contract",
  "expiry",
  "building_age",
];

const BACKEND_FIELD_TO_SLOT: Record<string, LeadSlotKey> = {
  business_segment: "segment",
  annual_usage_mwh: "usage",
  square_footage: "square_footage",
  contract_status: "provider_contract",
  has_provider: "provider_contract",
  expiry_months: "expiry",
  building_age_years: "building_age",
  final_tier: "tier_status",
};

const emptyState: LeadState = {
  segment: null,
  usage: null,
  square_footage: null,
  provider_contract: null,
  expiry: null,
  building_age: null,
  tier_status: "Intake",
};

export async function postLeadTurn(
  request: LeadTurnRequest,
  currentState: LeadState,
): Promise<LeadTurnResponse> {
  try {
    const requestBody: LeadTurnRequest = {
      ...request,
      state: toBackendState(currentState),
    };

    const response = await fetch(LEAD_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      throw new Error(`Lead endpoint returned ${response.status}`);
    }

    return normalizeLeadResponse((await response.json()) as LeadTurnResponse);
  } catch {
    return mockLeadTurn(request, currentState);
  }
}

export async function getLeadSessions(): Promise<LeadSessionsResponse> {
  try {
    const response = await fetch(LEAD_SESSIONS_ENDPOINT, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`Lead sessions endpoint returned ${response.status}`);
    }

    return normalizeLeadSessionsResponse((await response.json()) as LeadSessionsResponse);
  } catch {
    return { items: [], unavailable: true };
  }
}

export function getInitialLeadState(): LeadState {
  return { ...emptyState };
}

export function readLeadSlot(state: LeadState | null | undefined, key: LeadSlotKey) {
  if (!state) return undefined;

  if (key === "tier_status") {
    return (
      state.slots?.tier_status ??
      primitiveSlotValue(state.tier_status) ??
      slotLabel(state.backend_state?.final_tier) ??
      [state.tier, state.status].filter(Boolean).join(": ") ??
      undefined
    );
  }

  return state.slots?.[key] ?? primitiveSlotValue(state[key]) ?? readBackendSlot(state, key);
}

function mockLeadTurn(request: LeadTurnRequest, currentState: LeadState): LeadTurnResponse {
  const nextState = inferStateFromMessage(request.message, currentState);
  const missingFields = REQUIRED_FIELDS.filter((field) => !readLeadSlot(nextState, field));
  const classification = classifyLead(nextState, missingFields);
  const tierStatus = classificationToLabel(classification);
  const state = { ...nextState, tier_status: tierStatus };

  return {
    session_id: request.session_id || createSessionId(),
    response: buildMockResponse(request.message, missingFields, tierStatus),
    state,
    missing_fields: missingFields,
    classification,
    trace: { source: "frontend_mock" },
  };
}

function inferStateFromMessage(message: string, currentState: LeadState): LeadState {
  const normalized = message.toLowerCase();
  const nextState: LeadState = { ...emptyState, ...currentState };

  if (!readLeadSlot(nextState, "segment")) {
    const segment = matchFirst(normalized, [
      ["manufactur", "Manufacturing"],
      ["warehouse", "Warehouse / logistics"],
      ["office", "Office"],
      ["retail", "Retail"],
      ["restaurant", "Restaurant / hospitality"],
      ["school", "Education"],
      ["clinic", "Healthcare"],
      ["multi", "Multifamily"],
    ]);
    if (segment) nextState.segment = segment;
  }

  const usageMatch = message.match(/([\d,.]+)\s*(kwh|kw h|mwh|therms?)/i);
  if (usageMatch?.[1] && usageMatch?.[2]) {
    nextState.usage = `${usageMatch[1]} ${usageMatch[2].replace("kw h", "kWh")}`;
  }

  const squareFootageMatch = message.match(/([\d,.]+)\s*(sq\.?\s*ft|square feet|sf)/i);
  if (squareFootageMatch?.[1]) {
    nextState.square_footage = `${squareFootageMatch[1]} sq ft`;
  }

  const provider = matchFirst(normalized, [
    ["constellation", "Constellation"],
    ["direct energy", "Direct Energy"],
    ["nrg", "NRG"],
    ["engie", "ENGIE"],
    ["enbridge", "Enbridge"],
    ["duke", "Duke Energy"],
    ["aep", "AEP"],
    ["utility", "Utility default service"],
  ]);
  if (provider) nextState.provider_contract = provider;
  if (normalized.includes("contract") && !readLeadSlot(nextState, "provider_contract")) {
    nextState.provider_contract = "Contract details pending";
  }

  const expiryMatch = message.match(
    /(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}|\d{1,2}\/\d{1,2}\/\d{2,4}|\b20\d{2}\b/i,
  );
  if (expiryMatch?.[0]) {
    nextState.expiry = expiryMatch[0];
  } else if (normalized.includes("month") || normalized.includes("expire")) {
    nextState.expiry = "Expiry timing mentioned";
  }

  const ageMatch = message.match(/(\d{1,3})\s*(years? old|yrs? old|year-old)/i);
  const builtMatch = message.match(/built\s+(in\s+)?(19\d{2}|20\d{2})/i);
  if (ageMatch?.[1]) {
    nextState.building_age = `${ageMatch[1]} years`;
  } else if (builtMatch?.[2]) {
    nextState.building_age = `Built ${builtMatch[2]}`;
  }

  return nextState;
}

function classifyLead(
  state: LeadState,
  missingFields: LeadSlotKey[],
): Exclude<LeadClassification, string | null> {
  const usage = String(readLeadSlot(state, "usage") || "");
  const squareFootage = String(readLeadSlot(state, "square_footage") || "");
  const numericUsage = Number(usage.replace(/[^\d.]/g, ""));
  const numericFootage = Number(squareFootage.replace(/[^\d.]/g, ""));
  const isHighPotential =
    (usage.toLowerCase().includes("mwh") && numericUsage >= 1) ||
    numericUsage >= 250000 ||
    numericFootage >= 50000;

  if (missingFields.length === 0 && isHighPotential) {
    return { label: "Qualified opportunity", tier: "A", status: "Ready for advisor" };
  }

  if (missingFields.length <= 2) {
    return { label: "Review needed", tier: "B", status: "Needs contract detail" };
  }

  return { label: "Intake in progress", tier: "C", status: "Collecting fit data" };
}

function buildMockResponse(message: string, missingFields: LeadSlotKey[], tierStatus: string) {
  const normalized = message.toLowerCase();

  if (normalized.includes("estimate from facility size")) {
    return "Sure. Share the approximate square footage, facility segment, building age, and any major equipment loads from the prospect notes. I can estimate usage from there.";
  }

  if (normalized.includes("known usage") || normalized.includes("annual usage")) {
    return "Great. Send the prospect's annual kWh or MWh, current provider or contract type, and when the contract expires.";
  }

  if (missingFields.length === 0) {
    return `Thanks. I have the core qualification fields and this lead is marked ${tierStatus}. The internal team can review the usage profile, timing, and handoff notes next.`;
  }

  return `I captured that. Next, I need ${formatMissingFields(missingFields)} from the record or reviewer to complete the ABC Energy qualification.`;
}

function normalizeLeadResponse(response: LeadTurnResponse): LeadTurnResponse {
  const state = normalizeLeadState(response.state || getInitialLeadState());

  return {
    ...response,
    state,
    missing_fields: normalizeMissingFields(response.missing_fields || []),
    classification: response.classification ?? null,
  };
}

function normalizeLeadSessionsResponse(response: LeadSessionsResponse): LeadSessionsResponse {
  const items = Array.isArray(response.items) ? response.items : [];

  return {
    items: items.map(normalizeLeadSession),
  };
}

function normalizeLeadSession(session: LeadSession): LeadSession {
  return {
    ...session,
    latest_state: session.latest_state ? normalizeLeadState(session.latest_state) : null,
  };
}

function classificationToLabel(classification: LeadClassification) {
  if (!classification) return "Intake";
  if (typeof classification === "string") return classification;

  const label = classification.label || classification.status || "Intake";
  return classification.tier ? `${classification.tier}: ${label}` : label;
}

function formatMissingFields(fields: LeadSlotKey[]) {
  return fields
    .map((field) => field.replace("_", " "))
    .join(", ")
    .replace(/, ([^,]*)$/, ", and $1");
}

function matchFirst(text: string, patterns: Array<[string, string]>) {
  return patterns.find(([pattern]) => text.includes(pattern))?.[1];
}

function createSessionId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `lead-${Date.now()}`;
}

function normalizeLeadState(rawState: LeadState): LeadState {
  const backendState = rawState.backend_state || (rawState as BackendLeadState);
  const state: LeadState = { ...rawState, backend_state: backendState };
  const slots: Partial<Record<LeadSlotKey, string | number | null>> = {
    ...rawState.slots,
  };

  const segment = slotLabel(backendState.business_segment);
  if (segment) slots.segment = capitalize(segment);

  const usage = slotLabel(backendState.annual_usage_mwh);
  if (usage) slots.usage = `${usage} MWh`;

  const squareFootage = slotLabel(backendState.square_footage);
  if (squareFootage) slots.square_footage = `${squareFootage} sq ft`;

  const provider = slotLabel(backendState.has_provider);
  const contract = slotLabel(backendState.contract_status);
  if (provider !== undefined || contract) {
    const providerLabel =
      provider === "false"
        ? "No current provider"
        : provider === "true"
          ? "Provider in place"
          : undefined;
    slots.provider_contract = [providerLabel, formatContractStatus(contract)]
      .filter(Boolean)
      .join(" / ");
  }

  const expiry = slotLabel(backendState.expiry_months);
  if (expiry) slots.expiry = `${expiry} months`;

  const buildingAge = slotLabel(backendState.building_age_years);
  if (buildingAge) slots.building_age = `${buildingAge} years`;

  const finalTier = slotLabel(backendState.final_tier);
  if (finalTier) slots.tier_status = finalTier;

  state.slots = slots;
  return state;
}

function normalizeMissingFields(fields: string[]): LeadSlotKey[] {
  return Array.from(
    new Set(
      fields
        .map((field) => BACKEND_FIELD_TO_SLOT[field] || (field as LeadSlotKey))
        .filter((field): field is LeadSlotKey => REQUIRED_FIELDS.includes(field as LeadSlotKey)),
    ),
  );
}

function toBackendState(state: LeadState): BackendLeadState | null {
  return state.backend_state || null;
}

function readBackendSlot(state: LeadState, key: LeadSlotKey) {
  const backendState = state.backend_state;
  if (key === "segment") return slotLabel(backendState?.business_segment);
  if (key === "usage") return slotLabel(backendState?.annual_usage_mwh);
  if (key === "square_footage") return slotLabel(backendState?.square_footage);
  if (key === "expiry") return slotLabel(backendState?.expiry_months);
  if (key === "building_age") return slotLabel(backendState?.building_age_years);
  if (key === "provider_contract") {
    const provider = slotLabel(backendState?.has_provider);
    const contract = slotLabel(backendState?.contract_status);
    return [provider, contract].filter(Boolean).join(" / ") || undefined;
  }
}

function slotLabel(slot: unknown) {
  if (slot === null || slot === undefined || slot === "") return undefined;
  if (typeof slot !== "object") return primitiveSlotValue(slot);
  if (!("value" in slot)) return undefined;
  const value = (slot as { value?: unknown }).value;
  if (value === null || value === undefined || value === "") return undefined;
  return String(value);
}

function formatContractStatus(value?: string) {
  if (!value) return undefined;
  return value.replaceAll("_", " ");
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function primitiveSlotValue(value: unknown) {
  if (value === null || value === undefined || value === "") return undefined;
  if (typeof value === "string" || typeof value === "number") return String(value);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return undefined;
}
