import { useEffect, useState } from "react";
import {
  ArrowUp,
  Badge,
  BookOpen,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  CircleHelp,
  CreditCard,
  Construction,
  Gavel,
  Gauge,
  Globe2,
  Home as HomeIcon,
  HousePlus,
  Lock,
  MailCheck,
  MapPin,
  MessageCircle,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { api, type ApiResult, type HealthInfo } from "../api";

const ICONS: Record<string, LucideIcon> = {
  add_home_work: HousePlus,
  arrow_upward: ArrowUp,
  badge: Badge,
  check_circle: CheckCircle2,
  credit_card: CreditCard,
  construction: Construction,
  error: CircleAlert,
  expand_less: ChevronUp,
  expand_more: ChevronDown,
  forum: MessageCircle,
  gavel: Gavel,
  gauge: Gauge,
  home: HomeIcon,
  home_work: Building2,
  location_on: MapPin,
  lock: Lock,
  mark_email_read: MailCheck,
  menu_book: BookOpen,
  public: Globe2,
  sparkles: Sparkles,
  sync: RefreshCw,
  tune: Settings2,
  verified: ShieldCheck,
};

export function Icon({ name, size }: { name: string; size?: number }) {
  const Component = ICONS[name] ?? CircleHelp;
  return (
    <Component
      aria-hidden="true"
      className="icon"
      focusable="false"
      size={size}
      strokeWidth={2.25}
    />
  );
}

export function ThinkBlock({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="think">
      <button className="think-toggle" onClick={() => setOpen(!open)}>
        <Icon name={open ? "expand_less" : "expand_more"} />
        Thinking
      </button>
      <div className={`think-body${open ? " open" : ""}`}>
        <div className="think-inner">{text}</div>
      </div>
    </div>
  );
}

/* ── status bar (live health/ready) ── */

export function StatusBar() {
  const [health, setHealth] = useState<ApiResult<HealthInfo> | null>(null);
  const [ready, setReady] = useState<ApiResult<Record<string, unknown>> | null>(null);
  useEffect(() => {
    void api.health().then(setHealth);
    void api.ready().then(setReady);
  }, []);
  const pill = (label: string, r: ApiResult<unknown> | null) => {
    const ok = r?.kind === "ok";
    const cls = r === null ? "pill dim" : ok ? "pill ok" : "pill bad";
    const icon = r === null ? "sync" : ok ? "check_circle" : "error";
    return (
      <span className={cls}>
        <Icon name={icon} />
        {label}
      </span>
    );
  };
  const version = health?.kind === "ok" ? health.data.version : undefined;
  return (
    <div className="statusbar">
      {pill("api", health)}
      {pill("ready", ready)}
      <span className="grow" />
      <span>LotFile · /api/v1{version ? ` · v${version}` : ""} · advisory only — cited to approved sources, not a certification</span>
    </div>
  );
}
