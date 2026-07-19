import Link from "next/link";

export default function Home() {
  return (
    <>
      <section className="hero">
        <h1>
          あなたの&ldquo;取扱説明書&rdquo;を
          <br />
          数秘 × 科学で。
        </h1>
        <p>
          生年月日から導く数秘術の物語性と、心理学で最も信頼される
          ビッグファイブの科学性。2つをAIが融合して、
          あなただけの診断文をお届けします。
        </p>
      </section>

      <div className="card">
        <h2>できること</h2>
        <p>
          <span className="chip">数秘ラベル</span>
          <span className="chip">Big5レーダー</span>
          <span className="chip">AI診断文</span>
          <span className="chip">恋愛/ビジネス相性</span>
        </p>
        <p className="muted">
          所要時間は約2分。生年月日と10問の質問に答えるだけです。
          本名の入力は不要です。
        </p>
        <Link href="/diagnose" className="btn btn-primary" style={{ marginTop: 12 }}>
          無料で診断をはじめる
        </Link>
      </div>

      <div className="card">
        <h2>NUMENの3層</h2>
        <p className="muted">
          <b style={{ color: "var(--brand)" }}>数秘</b>
          ＝シェアしたくなる物語の入口（娯楽）。
          <br />
          <b style={{ color: "var(--brand)" }}>ビッグファイブ</b>
          ＝統計的裏付けのある性格の科学。
          <br />
          <b style={{ color: "var(--brand)" }}>AI</b>
          ＝2つを統合し、一人ひとりに最適化した読み物へ。
        </p>
      </div>

      <p className="notice">
        ※本診断は娯楽・自己理解を目的としたものであり、結果を保証するものではありません。
        生年月日は診断算出のみに使用します。
      </p>
    </>
  );
}
