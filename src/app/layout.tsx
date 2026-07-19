import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NUMEN — 数秘 × ビッグファイブ 診断",
  description:
    "生年月日の数秘術と、心理学のビッグファイブを掛け合わせ、AIがあなただけの診断文を生成します。",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body>
        <div className="shell">
          <div className="brandmark">
            <div className="logo">NUMEN</div>
            <div className="tag">数秘 × ビッグファイブ × AI</div>
          </div>
          {children}
        </div>
      </body>
    </html>
  );
}
