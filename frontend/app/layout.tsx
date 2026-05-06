import './globals.css';

export const metadata = {
  title: 'AI Second Brain',
  description: 'AI-powered personal knowledge base agent',
};

export default function RootLayout(props: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{props.children}</body>
    </html>
  );
}
