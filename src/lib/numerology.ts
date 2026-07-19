// 数秘術エンジン（要件定義書 §5.2）— 完全決定論・外部依存なし。
import config from "@config/numerology.json";
import type { LifePath } from "./types";

export interface NumerologyConfig {
  masterNumbers: {
    include11: boolean;
    include22: boolean;
    include33: boolean;
    include44: boolean;
  };
  reductionMethod: "sum-all" | "reduce-each-pillar";
}

const defaultConfig = config as unknown as NumerologyConfig;

/** 有効なマスターナンバー集合を設定から構築 */
export function masterSet(cfg: NumerologyConfig = defaultConfig): Set<number> {
  const s = new Set<number>();
  if (cfg.masterNumbers.include11) s.add(11);
  if (cfg.masterNumbers.include22) s.add(22);
  if (cfg.masterNumbers.include33) s.add(33);
  if (cfg.masterNumbers.include44) s.add(44);
  return s;
}

/** 各桁の合計 */
export function digitSum(n: number): number {
  return String(Math.abs(n))
    .split("")
    .reduce((acc, c) => acc + Number(c), 0);
}

/** 1桁（またはマスターナンバー）になるまで還元。マスターで停止する。 */
export function reduceNumber(
  n: number,
  master: Set<number> = masterSet()
): number {
  while (n > 9 && !master.has(n)) {
    n = digitSum(n);
  }
  return n;
}

/**
 * ライフパスナンバーを算出する。
 * reductionMethod:
 *  - "sum-all": 全桁を一括合計してから還元（デフォルト）
 *  - "reduce-each-pillar": 年・月・日を各々還元してから合計し、最後に還元
 */
export function lifePath(
  year: number,
  month: number,
  day: number,
  cfg: NumerologyConfig = defaultConfig
): LifePath {
  const master = masterSet(cfg);
  let total: number;
  if (cfg.reductionMethod === "reduce-each-pillar") {
    total =
      reduceNumber(digitSum(year), master) +
      reduceNumber(digitSum(month), master) +
      reduceNumber(digitSum(day), master);
  } else {
    total = digitSum(year) + digitSum(month) + digitSum(day);
  }
  return reduceNumber(total, master) as LifePath;
}

/** "YYYY-MM-DD" 文字列からライフパスを算出。妥当性検証つき。 */
export function lifePathFromISO(
  iso: string,
  cfg: NumerologyConfig = defaultConfig
): LifePath {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso.trim());
  if (!m) throw new Error(`不正な日付形式です（YYYY-MM-DD）: ${iso}`);
  const [, y, mo, d] = m;
  const year = Number(y);
  const month = Number(mo);
  const day = Number(d);
  // 実在日チェック（例: 2月30日を弾く）
  const dt = new Date(Date.UTC(year, month - 1, day));
  if (
    dt.getUTCFullYear() !== year ||
    dt.getUTCMonth() !== month - 1 ||
    dt.getUTCDate() !== day
  ) {
    throw new Error(`実在しない日付です: ${iso}`);
  }
  return lifePath(year, month, day, cfg);
}
