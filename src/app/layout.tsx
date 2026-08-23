import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NUMEN — 数秘 × ビッグファイブ 診断",
  description:
    "生年月日の数秘術と、心理学のビッグファイブを掛け合わせ、AIがあなただけの診断文を生成します。",
  // SNS拡散時のカード表示（§12 シェア率）
  openGraph: {
    title: "NUMEN — 数秘 × ビッグファイブ 診断",
    description:
      "生まれた日の数と、性格の科学から。約2分・10問であなたの&ldquo;取扱説明書&rdquo;を。",
    type: "website",
    locale: "ja_JP",
  },
  twitter: { card: "summary" },
};

// アクセシビリティ: ユーザーによる拡大を禁止しない（maximumScale は指定しない）
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f4efe6" },
    { media: "(prefers-color-scheme: dark)", color: "#15141b" },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body>
        <a href="#main" className="skip-link">
          本文へスキップ
        </a>
        <header className="masthead">
          <div className="masthead-inner">
            <a href="/" className="wordmark" aria-label="NUMEN ホーム">
              <span className="wordmark-mark" aria-hidden="true">
                ✦
              </span>
              <span className="wordmark-text">NUMEN</span>
            </a>
            <p className="masthead-tag">数秘の物語 × 性格の科学</p>
          </div>
          <div className="masthead-rule" aria-hidden="true" />
        </header>
        <main id="main" className="shell" tabIndex={-1}>
          {children}
        </main>
        <footer className="siteftr">
          <div className="siteftr-inner">
            <p>NUMEN</p>
            <nav aria-label="フッター">
              <ul className="ftr-links">
                <li>
                  <a href="/diagnose">自己診断</a>
                </li>
                <li>
                  <a href="/compatibility">相性診断</a>
                </li>
                <li>
                  <a href="/name">名前の数字</a>
                </li>
                <li>
                  <a href="/year">年運</a>
                </li>
                <li>
                  <a href="/match">マッチング</a>
                </li>
                <li>
                  <a href="/team">チーム相性（法人）</a>
                </li>
                <li>
                  <a href="/terms">ご利用にあたって</a>
                </li>
                <li>
                  <a href="/privacy">プライバシーポリシー</a>
                </li>
              </ul>
            </nav>
            <p className="muted">
              娯楽・自己理解を目的とした診断です。結果を保証するものではありません。
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
