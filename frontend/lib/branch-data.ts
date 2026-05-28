export type MessageRole = 'user' | 'assistant'

export interface Message {
  id: string
  role: MessageRole
  content: string
  mergedFromThreadId?: string
}

export interface ThreadNodeData {
  label: string
  messages: Message[]
  parentId: string | null
  forkedFromMessageId?: string
}

export interface Conversation {
  id: string
  title: string
  updatedAt: string
}

export const conversations: Conversation[] = [
  { id: 'c1', title: 'Transformer Architecture', updatedAt: '2h ago' },
]

export interface InitialNode {
  id: string
  position: { x: number; y: number }
  data: ThreadNodeData
}

export const initialNodes: InitialNode[] = [
  {
    id: 'main',
    position: { x: 0, y: 0 },
    data: {
      label: 'Main',
      parentId: null,
      messages: [
        {
          id: 'm1',
          role: 'user',
          content: 'Can you explain the transformer architecture at a high level?',
        },
        {
          id: 'm2',
          role: 'assistant',
          content:
            'A transformer is a stack of identical blocks. Each block has multi-head self-attention followed by a feed-forward network, with residual connections and layer norm around both. Tokens are embedded, positions added, and every layer lets each token attend to every other token in parallel — that parallelism is the key departure from RNNs.',
        },
        {
          id: 'm3',
          role: 'user',
          content: 'Why was this such a big deal compared to RNNs?',
        },
        {
          id: 'm4',
          role: 'assistant',
          content:
            'Three reasons: full parallelism across the sequence during training, constant path length between any two tokens (so long-range dependencies are easier to learn), and attention scales remarkably well with data and parameters — which unlocked the modern era of large models.',
        },
        {
          id: 'm5',
          role: 'assistant',
          mergedFromThreadId: 'attention',
          content:
            'Synthesis: attention projects each token into Query, Key, Value vectors; scores tokens via scaled dot-product (QKᵀ/√d); softmaxes into weights; mixes values accordingly. Multi-head splits this across subspaces so different heads can specialize.',
        },
      ],
    },
  },
  {
    id: 'attention',
    position: { x: 520, y: -120 },
    data: {
      label: 'Attention Deep Dive',
      parentId: 'main',
      forkedFromMessageId: 'm2',
      messages: [
        {
          id: 'a1',
          role: 'user',
          content: 'Go deeper on attention — what\'s actually happening mathematically?',
        },
        {
          id: 'a2',
          role: 'assistant',
          content:
            'Each token produces three vectors: Query, Key, Value. Attention(Q,K,V) = softmax(QKᵀ / √dₖ) · V. The dot product measures similarity between a query and every key, softmax turns those scores into weights, and the result is a weighted sum of values. The √dₖ keeps gradients stable as dₖ grows.',
        },
        {
          id: 'a3',
          role: 'assistant',
          content:
            'Multi-head splits the projections into h heads of dimension d/h. Each head learns to attend to different relationships in parallel — one might track syntax, another coreference. Outputs concat and project back, giving the model multiple representation subspaces for roughly the same compute.',
        },
      ],
    },
  },
  {
    id: 'alternatives',
    position: { x: 520, y: 360 },
    data: {
      label: 'Alternatives to Transformers',
      parentId: 'main',
      forkedFromMessageId: 'm2',
      messages: [
        {
          id: 'b1',
          role: 'user',
          content: 'Are there serious alternatives to transformers right now?',
        },
        {
          id: 'b2',
          role: 'assistant',
          content:
            'A few worth knowing: state-space models like Mamba (linear-time sequence mixing with selective state), RWKV (RNN-style inference with transformer-style training), and hybrid architectures that interleave attention with SSM blocks. They trade some in-context flexibility for much better long-context throughput.',
        },
      ],
    },
  },
]

export const initialEdges = [
  {
    id: 'e-main-attention',
    source: 'main',
    target: 'attention',
    sourceHandle: 'msg-m2',
    type: 'branch' as const,
  },
  {
    id: 'e-main-alternatives',
    source: 'main',
    target: 'alternatives',
    sourceHandle: 'msg-m2',
    type: 'branch' as const,
  },
]
