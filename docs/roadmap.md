# 实现路线

每个模块结束时项目都能跑起来、能看到效果。参考实现见 philoagents-course，
括号里是它对应文件的行数，用来估工作量——都很小。

## 模块 1：裸 LangGraph 对话

目标：游戏里点开诸葛亮，能对话，但不记得上一句。

要写的文件：

- `domain/character.py`（参考 philosopher.py，51 行）— 角色的数据结构
- `domain/prompts.py`（142 行）— 人设提示词
- `domain/character_factory.py`（120 行）— 角色注册表
- `application/conversation_service/workflow/state.py`（37 行）— 图的状态
- `application/conversation_service/workflow/chains.py`（62 行）— LLM 调用链
- `application/conversation_service/workflow/nodes.py`（68 行）— 节点
- `application/conversation_service/workflow/graph.py`（48 行）— 组图
- `application/conversation_service/generate_response.py` — 对外入口
- `config.py` — pydantic-settings 读环境变量（含 provider 切换字段）
- `infrastructure/api.py`（144 行）— FastAPI + WebSocket

## 模型提供商

决定（2026-09）：同时支持 Groq 和 OpenRouter，用 `.env` 里的 `LLM_PROVIDER` 切换。

- 开发和调提示词用 OpenRouter：能直接调 DeepSeek / Qwen / GLM / Kimi 这些中文原生模型，
  半文半白这种语域控制吃中文能力，Groq 的生产模型里没有中文强的（Qwen 只在 preview）
- 游戏体验优先时切回 Groq：Llama 3.3 70B 能到 280 tokens/秒，对话响应快得多
- 成本：OpenRouter 推理不加价，只在充值时收 5.5%（最低 $0.80，所以别小额充，一次充 $20）

实现收敛在 `chains.py` 的 `get_chat_model()` 一个函数里，返回类型标 `BaseChatModel`，
下游 `prompt | model` 不用动。这个多 provider 设计本身是简历上的一个点：
便于在模块 4 拿同一份评估集给不同模型打分。

## 模块 1 完成记录（2026-09）

踩过的坑，别再犯：

- `OPENROUTER_BASE_URL: "https://..."` 冒号当赋值用了 → 字符串被当成前向引用类型，
  报 `Forward reference must be an expression`。Python 没有 TS 的字符串字面量类型。
- 抄了参考实现的 `from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver`，
  该子模块在 0.5.0 已不存在 → import 失败 → 进程退出 → 前端 ERR_CONNECTION_REFUSED。
  教训：参考实现锁的是一年前的版本，"我这儿没有"先查版本。
- 角色卡里"不要写动作旁白"被无视，模型输出 `（轻摇羽扇）`。
  修法：否定式改肯定式 + 写进"规矩"第一条 + 带上真实反例 + 明确全角括号。
- 前端出生点是按 `config.name` 匹配 tilemap 对象名的，改中文名会 spawnPoint undefined。
  解法：加 `spawnName` 字段，显示名和出生点名分开。
- Phaser 的 atlas 方向帧按原角色名前缀命名，复用 sprite 必须传 `framePrefix`，
  否则 sprite 静默不显示（只有控制台警告，不抛异常）。

## 模块 2：短期记忆

- 换成 `AsyncMongoDBSaver` 作为 checkpointer
- `workflow/edges.py`（17 行）— 对话长了自动摘要的条件边
- 摘要节点

## 模块 2 完成记录（2026-09）

做了什么：

- `MongoDBSaver` 作为 checkpointer，thread_id 区分对话
- 摘要节点 + 条件边，超过 TOTAL_MESSAGES_SUMMARY_TRIGGER 条自动压缩历史
- MongoClient 在 lifespan 里建一次全程复用，不再每条消息新建连接
- `/reset-memory` 按 thread 清理，支持只清单个角色

可量化的收益（14 轮对话实测）：摘要生效后输入 token 从 1139 降到 911，
消息还多了两条。这个数字可以直接用在简历和面试里。

坑：

- 0.5.0 里 `AsyncMongoDBSaver` 和 `.aio` 子模块已删除，合并进 `MongoDBSaver`；
  `from_conn_string` 是同步上下文管理器，要用 `with` 而不是 `async with`。
  其异步方法是 `run_in_executor` 包的同步 pymongo，不是原生异步。
- 图的 input 里不能传 `"summary": ""`，普通字段是覆盖语义，每轮都会把摘要擦掉。
- 摘要提示词必须写明"必须保留：对方自称、具体人事物、角色做过的断言"，
  否则会被压成"两人讨论了天下大势"，玩家名字第一个丢。
- 清理 thread 要从库里 distinct 出实际存在的 thread_id 按前缀匹配，
  因为 new_thread=True 会生成 `<id>-<uuid>` 形态，只删 `<id>` 会留垃圾。

已知局限（面试可以主动讲）：

- thread_id 就是 character_id，所有玩家共用一条对话；多玩家需要 `<player_id>-<character_id>`
- `distinct()` 是同步调用，在 async 端点里会短暂阻塞事件循环

## 模块 3：RAG 长期记忆

- `application/data/extract.py` — 从《三国志》原文抽取人物史料
  （原计划抓中文维基，容器内网络不通，改用本地古籍文本，见下）
- `application/rag/splitters.py`（28 行）、`embeddings.py`（40 行）、`retrievers.py`（69 行）
- `application/long_term_memory.py`（78 行）
- `workflow/tools.py`（16 行）— 把检索包成 tool 挂进图里

## 模块 3 完成记录（2026-09）

做了什么：

- 数据源从中文维基改成本地古籍文本（殆知阁《三国志》白文）。
  `extract.py` 按卷头标记 `宋太中大夫国子博士闻喜裴松之注`（全文 65 处）切卷，
  用特征起始句定位到人，计数法剥掉【】里的裴松之注（占全文约 44%）。
- 司马懿故意没有史料：《三国志》成书于西晋，陈寿不能给本朝先祖立传，
  他全书只以"宣王"散见他传。没有硬凑，`extract` 对他返回空列表并打 warning。
- 切分用 `RecursiveCharacterTextSplitter`，分隔符换成文言句末虚词
  `["\n", "也", "矣", "焉", "耳", "乎", "曰", ""]`，`keep_separator="end"`，
  按字符数而不是 token 数计长度（中文一字约一 token，够用）。
- embedding 走 OpenRouter 云端 `baai/bge-m3`（1024 维），不在容器里下模型。
- MongoDB Atlas 向量索引带 `character_id` 过滤字段，检索时用 `pre_filter`
  锁定角色，避免诸葛亮答出曹操卷的内容。
- 检索包成 `@tool`，`bind_tools` 挂进图里，走 agentic RAG（模型自己决定要不要查）
  而不是每轮无条件检索。工具通过 `InjectedState` 拿 `character_id`，不暴露给模型。
- 入库 169 个 chunk：刘备 32、诸葛亮 23、曹操 48、孙权 36、周瑜 30。

效果对照（这条最适合写进简历）：

- 加 RAG 之前，问周瑜赤壁，他答出「樯橹灰飞烟灭」——苏轼的词，晚了八百年。
- 加 RAG 之后，答案落在吴书九的原文上：精兵三万、程普为左右督、
  军中疾病、黄盖献计火攻。

性能（加了 `infrastructure/timing.py` 的耗时埋点才看清）：

| 指标 | 换模型前 | 换模型后 |
| --- | --- | --- |
| 首字延迟 | 13.38s | 3.51s（−74%） |
| 整轮总计 | 16.11s | 4.85s（−70%） |
| 空 chunk 数 | 56 | 0 |

原因是 `deepseek-v4-flash-0731` 在正式输出前先吐了 56 个空 chunk 的
reasoning token，换成 `deepseek/deepseek-v3.2` 后消失。
带工具调用的一轮拆开看：4 次 LLM 调用 16.57s（86%），3 次检索 2.71s（14%）——
瓶颈从头到尾都是模型，不是向量库。

已知遗留项（面试可以主动讲）：

1. **数据源字符质量**。底本是影印 OCR，有 218 处「防」是坏字占位符
   （五卷 42674 字，占 0.51%；周瑜卷 92 处 / 7761 字，1.19%），
   至少顶替了三个不同的原字（防策=孙策、中防军=中护军、防冲鬬舰=蒙冲斗舰、
   钟防=钟会）。「防」本身又有正常用法，既不能替换也不能删除。
   已在 `normalize_variants` 的 docstring 里记档，不改数据源——
   现在换源要重做 extract 的整套定位逻辑，收益不如留着当已知上限。
   异体字部分已经修掉（见下）。
2. **周瑜卷是合传**。吴书九是周瑜鲁肃吕蒙合传，按卷取会混入另外两人的记载。
   同时代同阵营，对检索影响不大，metadata 里如实标注了。
3. **hybrid 检索没做**。BM25 + 向量的混合检索大概率能治人名检索，
   但现在没有评估集，做了也说不清好了多少。留到模块 4 有评估集之后再量化。

异体字归一（本次一并修掉）：

`extract.py` 加了 `VARIANT_CHARS`（68 条）+ `normalize_variants()`。
起因是「黄盖献计火攻」在周瑜卷里检索不到任何东西，而原文第一句就是
「瑜部将黄葢曰今冦众我寡难与持久」——底本写的是「黄葢」。
同类的还有闗/关、呉/吴、袆/祎、鬬/斗、畧/略、嵗/岁、髙/高 等。
**OpenCC 的 `t2s`/`tw2sp` 救不了**（实测全部原样输出），因为这些是异体字
不是繁体字，在 OpenCC 眼里它们本来就"是简体"，只是另一个字。
表是人工核对的：把五卷正文出现过的候选字逐个看上下文确认，
拿不准的不收（「夏侯楙」的「楙」是本名用字不是「茂」的异体，就没收）。
实现用 `str.maketrans` + `str.translate` 单遍扫描，不是链式 68 次 `replace`。
归一后「关羽」从 6 处涨到 37 处，正文总字数不变（1:1 映射）。

这一程被数据推翻的四个判断（记下来，是这个模块最值钱的部分）：

1. 「12s 延迟是工具调用和向量检索造成的」→ 埋点后发现是 reasoning token，
   检索只占 14%。**没测之前不要猜瓶颈。**
2. 「检索用具体的人名地名效果最好」（当时还写进了 tool 的 docstring）→
   实测长查询分数更高（0.6681 → 0.7463），短的专有名词表现最差。
   docstring 那句话要改。
3. 「不上 hybrid，BM25 帮不上忙」→ 专有名词恰恰是 BM25 的主场。
   当初的证据只覆盖了跨语域的语义查询，结论超出了证据范围。
4. 「黄盖查不到是切分把人名和内容切开了」→ 不是，是底本写「黄葢」。
   **先去看原始数据，再去改代码。**

还有一条方法论：相似度阈值过滤这条路走不通。分数分布实测下来，
负样本「今天天气怎么样」拿到 0.7198，比所有真实查询都高
（赤壁 0.7114、火攻 0.6754、黄盖 0.6680）——阈值切在哪里都是错的。
排序可信，绝对分数不可信。

坑：

- `create_vector_search_index` 第一次建索引不能传 `update=True`，
  要先 `list_search_indexes()` 看存不存在再决定。
- 容器跑的是旧镜像时改代码不生效。加了 bind mount + `fastapi dev`；
  日志里出现 `Starting FastAPI in production mode` 就是 reload 没开。
- tool 必须返回 `str`，返回 `list[Document]` 模型收不到内容。
- `chains.py` 里漏了 `.bind_tools(tools)`，表现是模型一次工具都不调，
  且不报错。
- `langchain_mongodb` 更新 vectorSearch 索引的路径是坏的：`create` 那条走
  `SearchIndexModel(..., type="vectorSearch")`，`update` 那条只传 name +
  definition，而 `updateSearchIndex` 命令本身没有 type 字段，服务端就按
  全文索引解释，报 `"mappings" is required`。索引定义只依赖维度和过滤字段
  这两个常量，所以正确做法是"已存在就跳过"，真要改定义就 drop 了重建。
- `make create-long-term-memory` 是独立的 `docker run`，沾不到
  docker-compose 里给 api 服务配的 bind mount，跑的是镜像里烘进去的旧代码。
  已把三个挂载同步到 Makefile。
  **判断方法：traceback 的行号跟眼前的文件对不上，就说明跑的不是这个文件。**
  这一条比读堆栈内容更快定位问题，应该作为第一反应。

## 模块 4：评估

- `application/evaluation/` — 生成数据集、上传、跑评估、自定义指标
- `tools/` 四个诊断脚本 — 判官选型、分层分析、导出最差样本、量指标本底
- Opik 打分

## 模块 4 完成记录（2026-09）

做了什么：

- `domain/evaluation.py` —— 评测集的数据模型（question / expected_answer /
  source_chunk / context_window / volume）。
- `application/evaluation/generate_dataset.py` —— 对语料 chunk 反向出题：
  让模型看着一段原文，写出"玩家会怎么问"。问题和答案天然对齐，不用人工标注。
- `upload_dataset.py` —— 推到 Opik。键名直接起成指标要的参数名
  （input / expected_output / context），省掉 scoring_key_mapping。
- `metrics.py` —— 两个自定义指标：`FaithfulnessToRetrieved`（把 context
  换成 agent 实际检索到的内容）和 `ToolCalled`（不调 LLM，是前者的分母）。
- `evaluate.py` —— `opik.evaluate` 编排。评估时**故意不挂 checkpointer**：
  单轮问答不需要持久化，挂上反而会让 196 条题共用对话历史。
- 四个诊断脚本：`compare_judges`（判官选型）、`analyze_experiment`（分层）、
  `dump_worst`（导出最差样本人肉归因）、`metric_floor`（正负对照量本底）。

最终基线（v2 数据集，196 条，判官 gpt-4o-mini）：

| 指标 | 值 | 方向 |
| --- | --- | --- |
| hallucination_vs_gold | 0.183 | 越低越好 |
| faithfulness_vs_retrieved | 0.132 | 越低越好 |
| answer_relevance | 0.908 | 越高越好 |
| tool_called | 0.941 | 越高越好 |

**尺子本身的刻度（最值钱的一条）：**

| 对照 | 均值 | 标准差 |
| --- | --- | --- |
| 正对照（参考答案当输出） | 0.015 | 0.053 |
| agent 实测 | 0.183 | — |
| 负对照（答非所问的套话） | 0.970 | 0.160 |

量程 0.015-0.970 几乎占满 [0,1]，本底噪声只有 0.015。**agent 那 0.183 里
92% 是真误差，8% 是本底**，后续任何 0.03 以上的改进都测得出来。

这个正负对照是模块 4 里最该留下的东西。它回答的不是"我的系统多好"，
而是"**我的测量能分辨多细**"——没有它，0.183 这个数不知道该不该信，
也不知道优化到哪一步该停。

一次结构性发现：

参考答案得 0.015，是因为它写得紧——一两句话，严格只用那段原文。
agent 得 0.183，是因为它按设计就要说得像个人：角色卡要求半文半白、
讲前因后果、有身份立场。他一带出背景，判官就判为 context 之外的内容。

所以这不是判官偏严，是**角色扮演的要求和 faithfulness 指标的要求在本质上
冲突**。剩下的 0.168 里混着两种东西：符合原著的合理发挥（想要的）和编造
（不想要的），而这个指标分不开。分开它们需要能看到全书的判官，或者换一个
指标（"答案里的事实性断言，有几条能在全书任意位置找到依据"）。留到模块 6。

这也解释了为什么把判官视野扩三倍只降了 0.007：agent 取材于整部演义和它的
参数记忆，不是相邻那两段，扩窗口追不上。

模块 3 遗留问题结案：**hybrid 检索不做。**

同子集对照（都调了检索的 168 条）：对 gold 一致 0.181，对 retrieved 忠实
0.163，差值只有 +0.018。"检索捞错东西"的特征是前者明显高于后者，实测在
噪声里。而且这个差还被高估了——演义同一件事横跨好几回，答案依据第 49 回、
gold 是第 50 回，判官看不见就算偏离。

但逐条人肉复核补上了一个均值看不到的东西：最差的 20 条里有 25% 栽在
"夏侯霸 vs 夏侯和"这类字面极近、指代不同的人名上，而这恰恰是 BM25 能救、
稠密向量救不了的。所以准确的结论是：**hybrid 没有可测量的整体收益，但对
"近形专有名词"这一个失败模式有明确的机制性理由；受影响样本只有 3%，做完
也测不出统计显著的提升。**这是个按机制决定、不是按数字决定的取舍。

判官选型（`tools/compare_judges.py`，同一批 10 条问答，agent 只跑一次）：

| 判官 | hallucination 均值 | 平均绝对差 | 价格 |
| --- | --- | --- | --- |
| gpt-4o-mini | 0.080 | — | $0.15/$0.60 |
| gpt-5-nano | 0.499 | 0.419 | $0.05/$0.40 |

nano 便宜三倍，排序也没乱（最好最差两条两边一致），但十条里八条落在
0.40-0.65，**往中间塌**——它验证不了事实时给中间分。没有分辨率，基线挤在
窄带里，后面 A/B 看不出变化。它在 answer_relevance 上跟 4o-mini 只差 0.100，
短板恰好落在"回答跟原文对不对得上"这个最难的判断上。

**判官一旦定了就不能换**：不同判官给的分不可比，换了之后报表上的分差是
判官变了不是系统变了，而且看不出来。

逐条复核的归因（最差 20 条，人工）：

| 类别 | 占比 | 指向 |
| --- | --- | --- |
| 出题质量差（缺时空定语、指代当前上下文、跨回拼装） | 35% | 改出题 prompt |
| 判官单 chunk 视野窄 | 30% | 扩 context_window |
| 检索分不清近形人名 | 25% | 精确匹配（可选） |
| 漏触发检索 / 检不到就脑补 | 15% | 改 docstring 和角色卡 |

**六成五的尾部误差来自测量本身，不是被测系统。**这条只有逐条看才发现得了——
汇总均值永远告诉你"有 18% 的问题"，不会告诉你其中一大半是你自己的尺子造成的。

已修（属于测量）：出题 prompt 加了"盖住原文自检"这条可执行动作（Case 8
那种"这段里你做了啥"的毒样本，根因是出题模型没意识到答题者看不到它的
上下文）；判官 context 从单 chunk 扩到同回前后各一段。

未修（属于系统，留给模块 6）：工具漏触发、检不到就脑补、近形人名。

一个白捡的发现：`tool_called` 从 0.857 涨到 0.941，而 agent 一行没改，
唯一的变化是题目变具体了。**问得含糊，模型就当是闲聊不去查。**

坑：

- Opik 算均值时会**排除** `scoring_failed` 的条目
  （`opik/evaluation/score_statistics.py`）。所以 `faithfulness` 只在"调了
  检索"的子集上算，`hallucination_vs_gold` 在全部样本上算——**两个数不是
  同一批样本，直接比是错的**。要判断瓶颈必须先分层。
- `{**dataset_item, **task_output}`：task 返回的键会覆盖 dataset 的同名键。
  所以 task 不能返回叫 `context` 的键，否则 gold 被顶掉，两个指标测同一个
  东西且不报错。
- `Hallucination` 不给 context **不会报错**，会静默换一套 prompt 去评笼统的
  事实准确性——被测对象被换掉，混进均值就再也看不出来。
- 带工具调用的那一轮，`AIMessage.content` 是空字符串（内容在 tool_calls 上）。
  直接取 `messages[-1]` 会把空串当答案交给判官。
- `opik.Opik()` 的 API key 是 `config.py` 的**导入副作用**设的。写一个没导
  config 的脚本就 401。这个隐式耦合该换成显式的 `configure_opik()`（遗留项）。
- 数据集改了结构就换名字。`insert` 是幂等追加，往旧的里灌会变成半新半旧
  的题，基线直接毁掉。

这一程被数据推翻的判断（第 5-8 个，接着模块 3 那四个数）：

5. 「nano 判不动会把分数压成 0 或 1」→ 实际是**往中间塌**。失败方式猜错了，
   但因为同时看了分布而不是只看均值，还是抓到了。
6. 「加了'必须在场''必须生前'两条规则，跳过数会明显上升；不涨就是规则没生效」
   → 跳过数从 13 降到 4。**判据本身立得不对**：两轮的 chunk 总体不同（1817 vs
   1336），数字不可比；而且上游 `_appears_in` 已经把不在场的段落滤掉了，
   轮到 prompt 看时没什么可跳的。该说"跳过数会变，但方向说不准，要看样本"。
7. 「扩判官视野能砍掉那 30% 的误判」→ gold 只动了 0.007。而且**我一次改了
   两个东西**（出题规则 + 判官视野），现在分不清是"扩视野没用"还是"有用但
   新题更难，两边抵消"。我上一轮刚强调过别混着改，然后自己犯了。
8. 「0.18 可能是指标天花板」→ 正对照 0.015，本底极低，尺子好得很。

方法论，三条：

- **均值有固有盲区。**检索失败很罕见但一旦发生就是灾难性的，会被 97% 的
  正常样本稀释掉。要看分布、要分层、要逐条读最差的那一批。
- **合成评测集永远测不出语料覆盖。**题目是从语料里生成的，它只能问语料里
  有的东西。"玩家想问的东西在不在语料里"这个问题，这套方法结构上回答不了。
- **改测量和改系统必须分开跑。**混在一起就再也分不清谁的功劳。（我自己违反
  了一次，代价是第 7 条那个说不清的结果。）

## 模块 5：迁移到 Postgres + pgvector

决定（2026-09）：模块 1-3 用 MongoDB，为的是能对照 philoagents 的参考实现；
模块 4 之后单独做一次迁移，作为项目里独立的一段经历。

迁移的理由（也是面试时要讲清楚的）：

- LangGraph Platform 生产部署的默认 checkpointer 就是 Postgres
- MongoDB checkpointer 单文档 16MB 上限，Postgres 单字段 1GB
- 5000 万向量以下 pgvector 的 TCO 比独立向量库低 40-60%
- 绝大多数公司已经在跑 Postgres，迁移面更宽

要改的：`AsyncMongoDBSaver` → `AsyncPostgresSaver`，
`MongoDBAtlasHybridSearchRetriever` → pgvector + tsvector 自己拼 hybrid。

## 模块 6：做成自己的东西

- 换角色美术（见下）
- 加一个原版没有的能力

## 前端要改的地方

角色是写死的，一共两处：

- `ui/src/scenes/Game.js:62` 附近的角色数组：`{ id, name, defaultDirection, roamRadius }`
- `ui/src/scenes/Preloader.js:28` 附近的 `this.load.atlas(...)`

素材在 `ui/public/assets/characters/<id>/`，每个角色一个 `atlas.png` + `atlas.json`。
第一版建议直接复用原有 sprite，只改 id 和中文名，美术留到最后再做。
