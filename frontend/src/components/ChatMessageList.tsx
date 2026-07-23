export type ChatMessage = {
  id: number
  role: 'user' | 'assistant'
  content: string
}

type ChatMessageListProps = {
  messages: ChatMessage[]
}

export function ChatMessageList({ messages }: ChatMessageListProps) {
  if (messages.length === 0) {
    return null
  }

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-1">
      {messages.map((message) => {
        const isUser = message.role === 'user'

        return (
          <article
            key={message.id}
            className={[
              'max-w-[85%] rounded-[1.75rem] px-5 py-4 text-left text-sm leading-6 shadow-sm',
              isUser
                ? 'self-end border border-sky-200/80 bg-sky-100/90 text-slate-900 shadow-[0_10px_30px_rgba(125,211,252,0.22)]'
                : 'self-start border border-slate-200 bg-white text-slate-800',
            ].join(' ')}
          >
            <p>{message.content}</p>
          </article>
        )
      })}
    </div>
  )
}