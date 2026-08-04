// パーソナルイヤー（年運）— 要件定義書 §3.2 / §8
// 算出: 誕生月 + 誕生日 + 対象年 を1桁まで還元する（年運は1〜9の循環として扱う）。
import data from "@data/personal_year.json";

export interface PersonalYearContent {
  year: number;
  theme: string;
  summary: string;
  dos: string[];
  donts: string[];
  love: string;
  work: string;
  disclaimer: string;
}

interface PersonalYearData {
  years: Record<string, PersonalYearContent>;
}

const content = data as unknown as PersonalYearData;

function digitSum(n: number): number {
  return String(Math.abs(n))
    .split("")
    .reduce((acc, c) => acc + Number(c), 0);
}

/** 年運は9年周期のため、マスターナンバーは残さず1〜9まで還元する */
function reduceToNine(n: number): number {
  while (n > 9) n = digitSum(n);
  return n;
}

/**
 * パーソナルイヤーを算出する。
 * @param birthMonth 誕生月（1-12）
 * @param birthDay   誕生日（1-31）
 * @param targetYear 対象の西暦年
 */
export function personalYear(
  birthMonth: number,
  birthDay: number,
  targetYear: number
): number {
  const total = digitSum(birthMonth) + digitSum(birthDay) + digitSum(targetYear);
  return reduceToNine(total);
}

/** パーソナルマンス（月運）。パーソナルイヤー + 対象月 を還元する */
export function personalMonth(personalYearNumber: number, month: number): number {
  return reduceToNine(personalYearNumber + month);
}

/** "YYYY-MM-DD" と対象年からパーソナルイヤーを算出 */
export function personalYearFromISO(iso: string, targetYear: number): number {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso.trim());
  if (!m) throw new Error(`不正な日付形式です（YYYY-MM-DD）: ${iso}`);
  return personalYear(Number(m[2]), Number(m[3]), targetYear);
}

export function getPersonalYearContent(n: number): PersonalYearContent {
  const c = content.years[String(n)];
  if (!c) throw new Error(`パーソナルイヤー ${n} の解説データが見つかりません`);
  return c;
}
