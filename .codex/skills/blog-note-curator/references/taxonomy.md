# Blog Note Taxonomy

Use this reference when the answer should become or update a blog note.

## Category Selection

- `LLM必备`: LLM concepts, training, inference, attention, tokenization, RAG, evaluation, alignment, model serving, prompt engineering when it is technical.
- `GPU相关`: CUDA, GPU architecture, memory hierarchy, mixed precision, profiling, kernels, performance debugging.
- `Triton算子`: Triton language, custom operators, kernel optimization, benchmark notes.
- `OS&网络`: operating systems, Linux, shell, Git, networking, storage, processes, containers, development environment issues.
- `CV必备`: computer vision, image models, metrics, losses, classical ML notes connected to CV.
- `行业展望`: technical industry analysis, platform shifts, product or ecosystem judgment with durable reasoning.
- `思考`: personal reflection, career judgment, learning method, long-term decision making.
- `杂项`: algorithms, data structures, math, Hexo/blogging, and useful technical notes that do not fit better elsewhere.

Prefer an existing specific category over `杂项`. Do not create a new category unless the topic is likely to grow into a recurring pillar.

## File Naming

- Use a short Chinese title when natural: `注意力机制中的KV缓存.md`.
- Keep common technical terms in English when that is clearer: `FlashAttention.md`, `git常识.md`.
- Avoid punctuation that makes shell paths awkward. Existing `+` and `&` are acceptable, but prefer simple names for new files.
- Place the file under `source/_posts/<category>/`.

## Publication Status

Use `published: false` by default for newly captured notes from Q&A. Change to `true` only when:

- the note has a clear title and excerpt
- the first section answers the question without relying on chat context
- examples are checked or clearly marked as illustrative
- the content is not just a rough scratchpad

## Existing Posts To Consider First

- Blog and Hexo workflow: `source/_posts/杂项/Hexo相关.md`, `source/_posts/OS&网络/Hexo+Obsidian+git.md`
- Git: `source/_posts/OS&网络/git常识.md`
- Mixed precision: `source/_posts/GPU相关/自动混合精度.md`
- Cross entropy and contrastive loss: `source/_posts/LLM必备/交叉熵与对比损失.md`
- Algorithms and data structures: `source/_posts/杂项/DP.md`, `source/_posts/杂项/堆.md`, `source/_posts/杂项/尾递归.md`, `source/_posts/杂项/搜索-回溯法.md`

Run the related-post search even when a likely file is listed here.
