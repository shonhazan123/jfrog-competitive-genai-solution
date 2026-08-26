import "./Quote.css";

interface QuoteProps {
  children: string;
}

export function Quote({ children }: QuoteProps) {
  return <blockquote className="quote">{children}</blockquote>;
}
