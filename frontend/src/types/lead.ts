export type LeadSlotKey =
  | "segment"
  | "usage"
  | "square_footage"
  | "provider_contract"
  | "expiry"
  | "building_age"
  | "tier_status";

export type SlotStatus = "unknown" | "inferred" | "confirmed";

export interface BackendLeadSlot<T = string | number | boolean> {
  value?: T | null;
  status?: SlotStatus;
}

export interface BackendLeadState {
  business_segment?: BackendLeadSlot<string>;
  annual_usage_mwh?: BackendLeadSlot<number>;
  square_footage?: BackendLeadSlot<number>;
  contract_status?: BackendLeadSlot<string>;
  expiry_months?: BackendLeadSlot<number>;
  has_provider?: BackendLeadSlot<boolean>;
  building_age_years?: BackendLeadSlot<number>;
  final_tier?: BackendLeadSlot<string>;
  reason?: BackendLeadSlot<string>;
}

export type LeadState = Partial<Record<LeadSlotKey, string | number | null>> & {
  slots?: Partial<Record<LeadSlotKey, string | number | null>>;
  backend_state?: BackendLeadState | null;
  status?: string | null;
  tier?: string | null;
};

export type LeadClassification =
  | string
  | {
      ready?: boolean;
      label?: string;
      tier?: string;
      status?: string;
      confidence?: number;
      reason?: string;
      matched_rule?: string | null;
    }
  | null;

export interface LeadTurnRequest {
  session_id?: string;
  message: string;
  state?: BackendLeadState | null;
}

export interface LeadTurnResponse {
  session_id: string;
  response: string;
  state: LeadState;
  missing_fields: LeadSlotKey[];
  classification: LeadClassification;
  trace?: unknown;
}

export interface LeadSession {
  session_id: string;
  final_tier?: string | null;
  matched_rule?: string | null;
  reason?: string | null;
  source?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  latest_state?: LeadState | null;
}

export interface LeadSessionsResponse {
  items: LeadSession[];
  unavailable?: boolean;
}
