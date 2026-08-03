// NUMEN 共通型定義（要件定義書 §5, §7）

export type LifePath = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 11 | 22 | 33;

export type Big5Key = "E" | "A" | "C" | "N" | "O";

/** 各因子 0–100 に正規化したスコア（レーダー表示・AI入力に使用） */
export type Big5Scores = Record<Big5Key, number>;

/** 各因子 1–7 スケールの素点（正規化前） */
export type Big5Raw = Record<Big5Key, number>;

export type Lens = "romance" | "business";
export type Mode = "self" | "compatibility";

/** 出力の深さ（§8 無料/有料の出し分け）: teaser=無料で見せる範囲 / full=LINE登録後 */
export type Depth = "teaser" | "full";

export interface Person {
  life_path: LifePath;
  big5: Big5Scores;
}

/** AI生成レイヤーへの構造化入力（要件定義書 §5.5） */
export interface DiagnosisInput {
  self: Person;
  target?: Person;
  lens: Lens;
  mode: Mode;
  /** 省略時は full（自己診断の無料枠は読み物を出す方針のため） */
  depth?: Depth;
}

export interface Big5Result {
  raw: Big5Raw; // 1–7
  scores: Big5Scores; // 0–100
}

export interface CompatibilityResult {
  lens: Lens;
  numerologyScore: number; // 0–100
  big5Score: number; // 0–100
  totalScore: number; // 0–100（重み付き）
  breakdown: {
    factor: Big5Key;
    mode: "similarity" | "complementarity";
    weight: number;
    score: number; // 0–100
  }[];
}

export interface NumberContent {
  number: number;
  isMaster: boolean;
  keywords: string[];
  essence: string;
  strengths: string[];
  mission: string;
  love: string;
  work: string;
  caution: string;
  disclaimer: string;
}
