import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

type MessageContentProps = {
  content: string
}

/**
 * SEC-9b: Render assistant replies as markdown.
 * 
 * Uses react-markdown with remark-gfm for tables, strikethrough, task lists.
 * Default config does NOT render raw HTML (safe against injection).
 */
export function MessageContent({ content }: MessageContentProps) {
  return (
    <div className="prose prose-sm max-w-none text-sm prose-p:my-2 prose-headings:my-3 prose-ul:my-2 prose-ol:my-2">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  )
}
