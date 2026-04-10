import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "国际遗产观察",
  description: "基于国际遗产观察文章库的问答对话界面。",
};

type RootLayoutProps = Readonly<{
  children: ReactNode;
}>;

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="zh-Hans">
      <body>
        <div className="site-root">{children}</div>
      </body>
    </html>
  );
}
