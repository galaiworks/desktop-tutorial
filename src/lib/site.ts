// 運営者情報（要件定義書 §13-4）。公開前に config/site.json を埋めること。
import config from "@config/site.json";

export interface SiteConfig {
  serviceName: string;
  operatorName: string;
  contactEmail: string;
  supervisorLabel: string;
  lastUpdated: string;
}

export const SITE = config as unknown as SiteConfig;

/** 運営者情報が公開に足る状態か（法務ページの警告表示に使う） */
export function isOperatorConfigured(): boolean {
  return Boolean(SITE.operatorName && SITE.contactEmail);
}
