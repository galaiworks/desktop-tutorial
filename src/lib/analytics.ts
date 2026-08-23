// 計測基盤（要件定義書 §6「各ステップの離脱・転換を全計測」／§12 KPI）
// プロバイダ非依存。GTM(dataLayer) / GA4(gtag) / Plausible があれば送り、無ければ無害に捨てる。
// 個人情報（生年月日・氏名）はイベントに載せない。載せるのは算出済みの匿名指標のみ。

export type NumenEvent =
  // 集客
  | "lp_view"
  | "diagnosis_start"
  // 診断
  | "birth_submitted"
  | "tipi_answer"
  | "tipi_complete"
  | "result_view"
  // 拡散
  | "share_click"
  | "code_copy"
  // 獲得（最重要KPI）
  | "line_cta_click"
  // 相性
  | "compatibility_start"
  | "compatibility_result_view"
  | "lens_switch";

type Props = Record<string, string | number | boolean | undefined>;

interface AnalyticsWindow extends Window {
  dataLayer?: unknown[];
  gtag?: (...args: unknown[]) => void;
  plausible?: (event: string, opts?: { props: Props }) => void;
}

/**
 * KPIイベントを送信する。
 * 送信先が未設定でも例外を出さない（拡散時に計測タグ未設定でも診断は動くべき）。
 */
export function track(event: NumenEvent, props: Props = {}): void {
  if (typeof window === "undefined") return;
  const w = window as AnalyticsWindow;
  const payload = { ...props, ts: Date.now() };

  try {
    w.dataLayer?.push({ event: `numen_${event}`, ...payload });
    w.gtag?.("event", event, payload);
    w.plausible?.(event, { props });
  } catch {
    // 計測の失敗が体験を壊さないようにする
  }

  if (process.env.NODE_ENV === "development") {
    // 開発時はコンソールでファネルを確認できるようにする
    console.debug("[numen:analytics]", event, payload);
  }
}
