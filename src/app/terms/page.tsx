import type { Metadata } from "next";
import { SCALE } from "@/lib/big5Scale";
import { SITE, isOperatorConfigured } from "@/lib/site";

export const metadata: Metadata = {
  title: "ご利用にあたって — NUMEN",
  description: "NUMENの利用条件と免責事項について。",
};

export default function Terms() {
  return (
    <article className="card">
      <p className="eyebrow story">法的事項</p>
      <h1 className="serif">ご利用にあたって</h1>

      <h2>1. 本サービスの位置づけ</h2>
      <p>
        NUMEN（以下「本サービス」）は、数秘術による物語的な読み解きと、
        性格心理学のビッグファイブ（五因子モデル）による測定を組み合わせた
        <b>娯楽および自己理解のためのコンテンツ</b>です。
        診断結果の的中や、特定の成果を保証するものではありません。
      </p>

      <h2>2. 免責事項</h2>
      <ul>
        <li>
          本サービスの結果は、医療・心理療法・法律・投資等の専門的助言に代わるものではありません。
        </li>
        <li>
          進路・就職・結婚・人間関係などの重要な意思決定を、本サービスの結果のみを根拠に
          行わないでください。
        </li>
        <li>
          相性スコアは、設定されたパラメータに基づく参考指標であり、
          人と人との関係の良し悪しを断定するものではありません。
        </li>
      </ul>

      <h2>3. 性格特性の取扱いについて</h2>
      <p>
        ビッグファイブの各因子に「良い・悪い」はありません。スコアはあくまで傾向を示すもので、
        個人の価値や能力を評価するものではありません。
        採用選考・人事評価などにおいて、本サービスの結果を唯一の判断根拠として
        用いることはお控えください。
      </p>

      <h2>4. 測定尺度について</h2>
      <p>
        ビッグファイブ（五因子モデル）そのものは、性格心理学において広く検証されてきた
        理論です。本サービスでは、その5因子を10項目で測定しています。
      </p>
      <p>
        使用尺度：<b>{SCALE.label}</b>
      </p>
      {SCALE.citation ? (
        <p className="muted">出典：{SCALE.citation}</p>
      ) : (
        <p className="muted">
          本尺度は当サービスが独自に作成したものです。
          <b>学術的な信頼性・妥当性の検証は行っていません。</b>
          結果は自己理解のきっかけとしてお楽しみください。
        </p>
      )}

      <h2>5. 知的財産</h2>
      <p>
        本サービスにおける各ナンバーの解説文その他のコンテンツは、
        本サービス提供者が独自に作成したものです。無断での転載・複製をお断りします。
      </p>

      <h2>6. 運営者</h2>
      {isOperatorConfigured() ? (
        <p>
          {SITE.operatorName}
          <br />
          お問い合わせ：{SITE.contactEmail}
        </p>
      ) : (
        <p className="err">
          【公開前に要記載】運営者名・連絡先が未設定です（config/site.json）。
        </p>
      )}

      <h2>7. 個人情報</h2>
      <p>
        個人情報の取扱いについては、
        <a href="/privacy">プライバシーポリシー</a>をご確認ください。
      </p>

      <p className="notice">
        本サービスをご利用いただいた時点で、上記の内容にご同意いただいたものとみなします。
      </p>
    </article>
  );
}
