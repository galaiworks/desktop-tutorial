// ナンバー解説データのローダ（要件定義書 §5.2 data/numbers/{n}.json）
import type { LifePath, NumberContent } from "./types";

import n1 from "@data/numbers/1.json";
import n2 from "@data/numbers/2.json";
import n3 from "@data/numbers/3.json";
import n4 from "@data/numbers/4.json";
import n5 from "@data/numbers/5.json";
import n6 from "@data/numbers/6.json";
import n7 from "@data/numbers/7.json";
import n8 from "@data/numbers/8.json";
import n9 from "@data/numbers/9.json";
import n11 from "@data/numbers/11.json";
import n22 from "@data/numbers/22.json";
import n33 from "@data/numbers/33.json";

const MAP: Record<number, NumberContent> = {
  1: n1 as NumberContent,
  2: n2 as NumberContent,
  3: n3 as NumberContent,
  4: n4 as NumberContent,
  5: n5 as NumberContent,
  6: n6 as NumberContent,
  7: n7 as NumberContent,
  8: n8 as NumberContent,
  9: n9 as NumberContent,
  11: n11 as NumberContent,
  22: n22 as NumberContent,
  33: n33 as NumberContent,
};

export function getNumberContent(n: LifePath): NumberContent {
  const c = MAP[n];
  if (!c) throw new Error(`ナンバー ${n} の解説データが見つかりません`);
  return c;
}

export const ALL_NUMBERS = Object.keys(MAP)
  .map(Number)
  .sort((a, b) => a - b) as LifePath[];
