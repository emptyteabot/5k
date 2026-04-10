import "./globals.css";

export const metadata = {
  title: "BYDFI Sentinel Dashboard",
  description: "Hermes-backed streaming dashboard for BYDFI AgentOS"
};

export default function RootLayout({ children }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
