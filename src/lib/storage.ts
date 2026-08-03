// 自己診断結果のローカル保持（相性診断で再入力させないため）
// 個人情報保護の観点から、保存するのは「算出結果」のみ。生年月日そのものは保存しない（§13-4）。
import type { Big5Scores, Lens, LifePath } from "./types";

const KEY = "numen.self.v1";

export interface StoredSelf {
  life_path: LifePath;
  big5: Big5Scores;
  lens: Lens;
  saved_at: string;
}

export function saveSelf(data: Omit<StoredSelf, "saved_at">): void {
  if (typeof window === "undefined") return;
  try {
    const payload: StoredSelf = { ...data, saved_at: new Date().toISOString() };
    window.localStorage.setItem(KEY, JSON.stringify(payload));
  } catch {
    // プライベートモード等で保存できなくても診断自体は継続させる
  }
}

export function loadSelf(): StoredSelf | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredSelf;
    if (!parsed?.life_path || !parsed?.big5) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function clearSelf(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    // 失敗しても致命的ではない
  }
}
