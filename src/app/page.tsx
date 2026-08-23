import Link from "next/link";

export default function Home() {
  return (
    <>
      <section className="hero">
        <p className="kicker">数秘 × ビッグファイブ</p>
        <h1>
          生まれた日の数と、
          <br />
          性格の科学から。
        </h1>
        <p className="lead">
          生年月日が導く数秘術の物語と、心理学で最も検証されてきた性格モデル
          「ビッグファイブ」。ふたつをAIが読み解き、あなたのための一篇に仕立てます。
        </p>
        <div className="btn-row">
          <Link href="/diagnose" className="btn btn-primary">
            無料で診断をはじめる
          </Link>
          <Link href="/compatibility" className="btn btn-outline">
            気になる人との相性を見る
          </Link>
        </div>
        <p className="muted" style={{ marginTop: 12 }}>
          所要 約2分・10問／本名の入力は不要です。
        </p>
      </section>

      <div className="card story">
        <p className="eyebrow story">物語の入口</p>
        <h2 className="serif">数秘というラベル</h2>
        <p className="muted">
          生年月日から一つの数（ライフパスナンバー）を導きます。
          そのナンバーが、あなたの性質を語る&ldquo;顔&rdquo;になります。
          楽しみながら自分を眺めるための、入口です。
        </p>
      </div>

      <div className="card science">
        <p className="eyebrow science">科学の裏づけ</p>
        <h2>ビッグファイブ（5因子）</h2>
        <p className="muted">
          外向性・協調性・勤勉性・情緒安定性・開放性。10問で測り、
          レーダーと数値で可視化します。物語とは層を分けて、
          &ldquo;測れるもの&rdquo;として扱います。
        </p>
      </div>

      <div className="card">
        <p className="eyebrow story" style={{ color: "var(--brass)" }}>
          そして
        </p>
        <h2 className="serif">AIが、二層を一篇に。</h2>
        <div className="duo" style={{ marginTop: 8 }}>
          <div className="pane story">
            <h3>数秘</h3>
            <p>物語・シェアしたくなるラベル（娯楽）</p>
          </div>
          <div className="pane science">
            <h3>ビッグファイブ</h3>
            <p>統計的裏づけのある性格の科学</p>
          </div>
        </div>
        <p className="muted" style={{ marginTop: 14 }}>
          番号もスコアも相性も、計算はすべてコードで確定。AIはその事実を
          &ldquo;読み物&rdquo;にするだけなので、数値がぶれることはありません。
        </p>
      </div>

      <div className="card">
        <p className="eyebrow story">ほかにもできること</p>
        <h2 className="serif">数字を、いろいろな角度から</h2>
        <ul className="menu-list">
          <li>
            <Link href="/name">
              <b>名前の数字</b>
              <span>才能・本音・印象を示す3つの数（ディスティニー他）</span>
            </Link>
          </li>
          <li>
            <Link href="/year">
              <b>年運（パーソナルイヤー）</b>
              <span>いまが9年周期のどの季節かを知る</span>
            </Link>
          </li>
          <li>
            <Link href="/match">
              <b>マッチング</b>
              <span>相性の高い人をおすすめから探す</span>
            </Link>
          </li>
          <li>
            <Link href="/team">
              <b>チーム相性（法人向け）</b>
              <span>メンバー間の総当たり相性と、チームの傾向</span>
            </Link>
          </li>
        </ul>
      </div>

      <p className="notice">
        本診断は娯楽・自己理解を目的としたもので、結果を保証するものではありません。
        生年月日は診断の算出のみに使用します。
      </p>
    </>
  );
}
