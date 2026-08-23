// 融合ロジック（要件定義書 §5.4）: 数秘=ラベル、Big5=補正。
// ここでは「AIに渡す前の確定した読み筋（決定的部分）」を組み立てる。読み物化はAIレイヤーの責務。
//
// ⚠ このモジュールは有料コンテンツ（本質・使命・強み等）を読み込むため **サーバー専用**。
//    クライアントからは headline.ts / contentPublic.ts を使うこと。
import type { Big5Scores, Lens, LifePath, NumberContent } from "./types";
import { getNumberContent } from "./content";
import { big5Descriptors, fusionHeadline } from "./headline";

export { levelOf, big5Descriptors, fusionHeadline } from "./headline";
export type { Level } from "./headline";

export interface FusionFacts {
  lifePath: LifePath;
  content: NumberContent;
  big5: Big5Scores;
  descriptors: ReturnType<typeof big5Descriptors>;
  headline: string;
  lens: Lens;
}

/** AI生成レイヤーに渡す確定事実の束を構築（ハルシネーション防止：AIはこれを創作しない）。 */
export function buildFusionFacts(
  lifePath: LifePath,
  big5: Big5Scores,
  lens: Lens
): FusionFacts {
  return {
    lifePath,
    content: getNumberContent(lifePath),
    big5,
    descriptors: big5Descriptors(big5),
    headline: fusionHeadline(lifePath, big5),
    lens,
  };
}
