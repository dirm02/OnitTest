"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  Building2,
  Clock3,
  Database,
  Gauge,
  RefreshCw,
  ShieldCheck,
  SquareStack,
} from "lucide-react";
import {
  Badge,
  Button,
  ScrollArea,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui";
import { getLeadSessions, readLeadSlot } from "@/lib/lead-api";
import { cn } from "@/lib/utils";
import type { LeadSession } from "@/types/lead";

type SavedLeadsPanelProps = {
  refreshKey?: number;
};

export function SavedLeadsPanel({ refreshKey = 0 }: SavedLeadsPanelProps) {
  const [sessions, setSessions] = useState<LeadSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isUnavailable, setIsUnavailable] = useState(false);

  const loadSessions = useCallback(async (mode: "initial" | "refresh" = "refresh") => {
    if (mode === "initial") {
      setIsLoading(true);
    } else {
      setIsRefreshing(true);
    }

    const response = await getLeadSessions();
    setSessions(response.items);
    setIsUnavailable(Boolean(response.unavailable));
    setIsLoading(false);
    setIsRefreshing(false);
  }, []);

  useEffect(() => {
    void loadSessions("initial");
  }, [loadSessions, refreshKey]);

  return (
    <section className="rounded-lg border border-[#d9ded1] bg-white">
      <div className="flex items-start justify-between gap-3 p-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold">Saved leads</h2>
            {isUnavailable ? (
              <Badge className="border-[#e5d0b6] bg-[#fff8ed] text-[#7a4d14]" variant="outline">
                Offline
              </Badge>
            ) : null}
          </div>
          <p className="mt-1 text-sm text-[#5f6b62]">Recent ABC Energy qualification sessions.</p>
        </div>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                aria-label="Refresh saved leads"
                className="h-9 w-9 border-[#ccd5c7] p-0 text-[#254c3a]"
                disabled={isLoading || isRefreshing}
                onClick={() => void loadSessions()}
                type="button"
                variant="outline"
              >
                <RefreshCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Refresh saved leads</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      <div className="border-t border-[#e2e5dd]">
        {isLoading ? (
          <SavedLeadsMessage icon={Clock3} title="Loading sessions" />
        ) : sessions.length === 0 ? (
          <SavedLeadsMessage
            icon={isUnavailable ? AlertCircle : Database}
            title={isUnavailable ? "Saved leads unavailable" : "No saved leads yet"}
            detail={
              isUnavailable
                ? "The sessions endpoint did not respond, so the workspace is showing an empty saved list."
                : "Completed backend sessions will appear here once they are available."
            }
          />
        ) : (
          <ScrollArea className="max-h-[360px]">
            <div className="space-y-3 p-3">
              {sessions.map((session) => (
                <SavedLeadRow key={session.session_id} session={session} />
              ))}
            </div>
          </ScrollArea>
        )}
      </div>
    </section>
  );
}

function SavedLeadRow({ session }: { session: LeadSession }) {
  const state = session.latest_state;
  const tier = session.final_tier || readLeadSlot(state, "tier_status") || "Unassigned";
  const segment = readLeadSlot(state, "segment") || "Segment pending";
  const usage = readLeadSlot(state, "usage") || "Usage pending";
  const squareFootage = readLeadSlot(state, "square_footage");
  const provider = readLeadSlot(state, "provider_contract") || "Provider pending";
  const updated = formatUpdatedDate(session.updated_at || session.created_at);

  return (
    <article className="rounded-lg border border-[#e2e5dd] bg-[#fbfcf8] p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="border-[#b8c6b4] bg-white text-[#254c3a]" variant="outline">
              {tier}
            </Badge>
            {session.source ? (
              <span className="truncate text-xs text-[#6d776e]">{session.source}</span>
            ) : null}
          </div>
          <h3 className="mt-2 truncate text-sm font-semibold text-[#253027]">{segment}</h3>
        </div>
        <div className="flex shrink-0 items-center gap-1 text-xs text-[#6d776e]">
          <Clock3 className="h-3.5 w-3.5" />
          {updated}
        </div>
      </div>

      <div className="mt-3 grid gap-2 text-xs text-[#4b564d]">
        <SavedLeadFact icon={Gauge} label={String(usage)} />
        <SavedLeadFact icon={ShieldCheck} label={String(provider)} />
        {squareFootage ? <SavedLeadFact icon={SquareStack} label={`${squareFootage}`} /> : null}
      </div>

      {(session.matched_rule || session.reason) && (
        <div className="mt-3 rounded-md border border-[#e5ebdf] bg-white px-3 py-2">
          {session.matched_rule ? (
            <p className="truncate text-xs font-medium text-[#254c3a]">{session.matched_rule}</p>
          ) : null}
          {session.reason ? (
            <p className="mt-1 line-clamp-2 text-xs leading-5 text-[#5f6b62]">{session.reason}</p>
          ) : null}
        </div>
      )}
    </article>
  );
}

function SavedLeadFact({ icon: Icon, label }: { icon: typeof Building2; label: string }) {
  return (
    <div className="flex min-w-0 items-center gap-2">
      <Icon className="h-3.5 w-3.5 shrink-0 text-[#2f6f4e]" />
      <span className="truncate">{label}</span>
    </div>
  );
}

function SavedLeadsMessage({
  icon: Icon,
  title,
  detail,
}: {
  icon: typeof Building2;
  title: string;
  detail?: string;
}) {
  return (
    <div className="flex min-h-[180px] flex-col items-center justify-center px-5 py-8 text-center">
      <div className="rounded-lg bg-[#eef6f8] p-2 text-[#28505e]">
        <Icon className="h-4 w-4" />
      </div>
      <p className="mt-3 text-sm font-medium text-[#253027]">{title}</p>
      {detail ? (
        <p className="mt-1 max-w-[260px] text-xs leading-5 text-[#6d776e]">{detail}</p>
      ) : null}
    </div>
  );
}

function formatUpdatedDate(value?: string | null) {
  if (!value) return "No date";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "No date";

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}
