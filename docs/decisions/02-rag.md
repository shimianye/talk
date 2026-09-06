# 第 2 章 · RAG 决策

> 记录日期：2026-09-06 ｜ 基准 commit：`3f28f4c` ｜ 状态定义见 [README](./README.md)

本章记录「知识怎么切、向量怎么算、检索怎么召回、兜底怎么降级」四个层面的取舍。

---

## D2-1 混合检索：pgvector 向量 + BM25 关键词 + RRF 融合

- **状态**：已采纳（待真实 Embedding 验证）
- **背景**：客服场景有两类查询——「iPhone 15 Pro 多少钱」这类**精确词**（型号、参数），和「适合打游戏的手机」这类**语义**查询。纯向量检索对精确词召回不稳，纯关键词检索对同义改写无能为力。
- **决策**：双路召回后用 RRF（Reciprocal Rank Fusion）融合排名，向量路捕捉语义、BM25 路捕捉精确词，RRF 免去调权重。
  - 实现位置：`backend/app/core/rag/retriever.py`（`hybrid_retrieve` / `_rrf_fuse`）。
  - 融合公式：`1/(k + rank + 1)`，`k=60`；结果同时保留 `similarity` / `bm25` / `vector` 三列分数，便于回溯哪一路贡献了召回。
- **放弃的替代方案**：
  - *纯向量检索*：型号词、错误码等精确匹配会漏。放弃。
  - *纯 BM25*：语义改写（「游戏手机」→ 高性能机型）会漏。放弃。
  - *加权求和融合*：需要人工调权重、对量纲敏感。RRF 只依赖排名，更稳。放弃。
- **失效条件**：语料从当前 20 篇 kb-docs 增长到数万 chunk、或对召回质量要求进入「榜单级」时，纯 Python 全量计算两路会变慢，需迁移到专业的向量库（如 pgvector 的 HNSW 索引 + 独立 BM25 引擎）并做召回评测。

---

## D2-2 零依赖纯 Python BM25，不引入搜索引擎

- **状态**：已采纳
- **背景**：关键词检索的「正解」是 Elasticsearch 或 Postgres FTS，但对一个 20 篇知识文档的客服 demo，引入 ES 是运维负担，引入 PG 中文 FTS 需要装扩展、配分词。
- **决策**：自己实现 Okapi BM25（`k1=1.5, b=0.75`），配合中文 bigram 分词，零外部依赖，测试确定性。
  - 实现位置：`backend/app/core/rag/retriever.py`（`class BM25`）。
- **放弃的替代方案**：
  - *Elasticsearch/Meilisearch*：多一个常驻服务，本地/CI 部署变重。放弃。
  - *Postgres FTS（`tsvector`）*：中文分词要额外装 `zhparser`/`pg_jieba`，运维成本高。放弃。
- **失效条件**：语料规模、QPS 或召回质量要求上来后，手写 BM25 在性能和中文分词质量上都不够，需换专业检索后端。

---

## D2-3 Mock Embedding 兜底 + 可插拔远程 BGE-M3

- **状态**：已采纳（待真实 Embedding 验证）
- **背景**：真实 Embedding（BGE-M3 等）需要 GPU 服务或付费 API；离线开发、CI、确定性评测都需要一个「能跑、且结果可复现」的向量源。
- **决策**：定义 `EmbeddingProvider` 抽象，`MockEmbeddingProvider` 用「词袋哈希 + L2 归一化」生成确定性的 1024 维向量（共享词元 → 更高余弦相似度），`RemoteEmbeddingProvider` 对接 OpenAI 兼容接口（可接 TEI 部署的 BGE-M3 或 Ollama），由配置切换。
  - 实现位置：`backend/app/core/rag/embedding.py`、`config.py`（`embedding_provider` / `embedding_model="bge-m3"` / `embedding_dim=1024`）。
  - 维度固定 1024，与 `pgvector` 列维度一致（`models/knowledge.py`）。
- **放弃的替代方案**：
  - *直接依赖 OpenAI Embedding API*：需 Key + 网络，离线不可用。放弃。
  - *纯 Mock 不做真实实现*：真实语义检索会缺失，所以远程实现已就位、只差服务。
- **失效条件**：Mock 的哈希词袋只是词法近似，**一旦进入真实语义检索，Mock 向量结果不可作为质量结论**，必须切到 BGE-M3 并重新验证。

---

## D2-4 中文 bigram 分词 + 英文按词，零依赖切词

- **状态**：已采纳
- **背景**：BM25 需要分词。中文没有空格边界，jieba 虽成熟但引入分词词典与依赖；对客服短查询，bigram（相邻二字组合）通常够用且无词典。
- **决策**：中文连续串切成二元组，英文/数字按词切（正则 `[\u4e00-\u9fff]+|[a-zA-Z0-9]+`），统一小写。
  - 实现位置：`backend/app/core/rag/retriever.py`（`_tokenize`）。
- **放弃的替代方案**：*jieba*（多一个依赖 + 词典，且对型号/参数等 OOV 词同样可能切错，收益有限）——放弃。
- **失效条件**：出现大量 OOV 长尾词、或查询变长到需要词性/句法时，bigram 召回变差，需引入专业分词或子词模型。

---

## D2-5 段落聚合切分，chunk_size=500 / overlap=60

- **状态**：已采纳
- **背景**：切块太碎会丢失上下文，太整会稀释向量语义。客服知识多为短条目，适合按段落聚合。
- **决策**：优先按段落（双换行）聚合到 500 字符上限；超长段落按句末标点切，相邻片段保留 60 字符重叠。
  - 实现位置：`backend/app/core/rag/chunker.py`（`chunk_text` / `_split_long`）。
- **放弃的替代方案**：*固定长度硬切*（会在句子中间截断）——放弃；*语义分块/模型分块*（当前规模过度）。
- **失效条件**：知识文档变长、结构变复杂（表格/多级标题）后，纯段落聚合会跨语义，需升级为结构化分块。

---

## D2-6 检索降级：混合命中为空 → ILIKE 文本兜底

- **状态**：已采纳
- **背景**：若向量库为空或 Embedding 服务异常，检索不应直接失败，客服应退化为「能查到什么算什么」。
- **决策**：`retrieve_with_fallback` 先混合检索，命中为空时降级为数据库 `ILIKE` 精确文本匹配（返回 `method="text"` 标记降级路径）。
  - 实现位置：`backend/app/core/rag/retriever.py`（`retrieve_with_fallback` / `_text_retrieve`）。
- **放弃的替代方案**：*检索失败即报错转人工*——体验差，且掩盖了「本可降级」的弹性。放弃。
- **失效条件**：ILIKE 兜底在语料变大后性能退化、且无法语义匹配，届时兜底应换为「带同义词的 FTS」而非纯 ILIKE。

---

## 小结

RAG 层的取舍主线是 **「零依赖先把链路跑通，留好真实实现的接口」**：混合检索 + 手写 BM25 + Mock 向量，让本地/CI/评测都能跑、能复现；真实 BGE-M3 的接口已就位，只差接服务。代价是 Mock 向量的结果不能当语义质量结论——这是必须诚实告知评审的边界（见第 4 章）。
