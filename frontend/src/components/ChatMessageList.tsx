import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeSanitize from 'rehype-sanitize'

export type ChatMessage = {
  id: number
  role: 'user' | 'assistant'
  content: string
}

type ChatMessageListProps = {
  messages: ChatMessage[]
  isStreaming: boolean
}

export function ChatMessageList({ messages, isStreaming }: ChatMessageListProps) {
  if (messages.length === 0) {
    return null
  }

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto rounded-2xl border border-slate-200/75 bg-slate-50/55 p-3 sm:p-4">
      {messages.map((message) => {
        const isUser = message.role === 'user'
        const showThinkingPlaceholder = !isUser && isStreaming && message.content.trim().length === 0

        return (
          <article
            key={message.id}
            className={[
              'max-w-[82%] rounded-2xl px-5 py-4 text-left text-sm leading-6 shadow-sm',
              isUser
                ? 'self-end border border-sky-200/80 bg-sky-100/90 text-slate-900 shadow-[0_10px_30px_rgba(125,211,252,0.22)]'
                : 'self-start border border-slate-200 bg-white text-slate-800 shadow-[0_8px_24px_rgba(15,23,42,0.08)]',
            ].join(' ')}
          >
            {showThinkingPlaceholder ? (
              <p className="text-slate-600">Thinking...</p>
            ) : isUser ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : (
              <div className="chat-markdown">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeSanitize]}
                  components={{
                    a: ({ node: _node, ...props }) => (
                      <a {...props} target="_blank" rel="noopener noreferrer" />
                    ),
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            )}
          </article>
        )
      })}
    </div>
  )
}