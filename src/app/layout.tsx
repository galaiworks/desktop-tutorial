import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NUMEN — 数秘 × ビッグファイブ 診断",
  description:
    "生年月日の数秘術と、心理学のビッグファイブを掛け合わせ、AIがあなただけの診断文を生成します。",
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
            <p className="muted">
              娯楽・自己理解を目的とした診断です。結果を保証するものではありません。
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
