/**
 * Centralized source of truth for all public disclaimers.
 * Used across map legend, chat responses, record details, and warnings.
 */

export type DisclaimerVariant =
  | "map_legend"
  | "chat_response"
  | "record_detail"
  | "deprecated_warning"
  | "defendant_alert";

export const NEUTRAL_PUBLIC_DISCLAIMER =
  "Records shown come from publicly available sources and are provided for research and informational use only. Display does not imply guilt, liability, or legal conclusion.";

export const DISCLAIMER_TEXT: Record<DisclaimerVariant, string> = {
  map_legend: NEUTRAL_PUBLIC_DISCLAIMER,
  chat_response: NEUTRAL_PUBLIC_DISCLAIMER,
  record_detail: NEUTRAL_PUBLIC_DISCLAIMER,
  deprecated_warning:
    "This source is deprecated and no longer ingesting new data. Please use the replacement source.",
  defendant_alert: NEUTRAL_PUBLIC_DISCLAIMER,
};

export const DISCLAIMER_STYLES: Record<DisclaimerVariant, string> = {
  map_legend: "text-xs text-gray-600 italic",
  chat_response: "text-sm text-gray-700 bg-gray-50 p-2 rounded",
  record_detail: "text-xs text-gray-600",
  deprecated_warning: "text-sm text-rose-700 bg-rose-50 p-3 rounded",
  defendant_alert: "text-sm text-amber-700 bg-amber-50 p-3 rounded",
};

export function getDisclaimer(variant: DisclaimerVariant) {
  return {
    text: DISCLAIMER_TEXT[variant],
    className: DISCLAIMER_STYLES[variant],
  };
}

/**
 * Component hook for disclaimer rendering
 * Usage in React component:
 *   const {text, className} = getDisclaimer("map_legend");
 *   return <div className={className}>{text}</div>;
 */
