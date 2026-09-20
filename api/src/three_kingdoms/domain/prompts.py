import opik
from loguru import logger


class Prompt:
    def __init__(self, name: str, prompt: str) -> None:
        self.name = name

        try:
            self.__prompt = opik.Prompt(name=name, prompt=prompt)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Can't use Opik to version the prompt (probably due to missing "
                "or invalid credentials). Falling back to local prompt. "
                "The prompt is not versioned, but it's still usable."
            )
            self.__prompt = prompt

    @property
    def prompt(self) -> str:
        if isinstance(self.__prompt, opik.Prompt):
            return self.__prompt.prompt
        else:
            return self.__prompt

    def __str__(self) -> str:
        return self.prompt

    def __repr__(self) -> str:
        return self.__str__()


__CHARACTER_CARD = """
你正在扮演{{character_name}}，一个真实活过的人。你不是在演戏——你就是他本人，此刻正与眼前这个人交谈。

---

姓名：{{character_name}}
身份与立场：{{character_perspective}}
言谈风格：{{character_style}}

---

说话的方式：

- 半文半白：文言的骨，白话的肉。像"此事需从长计议"这样。不要说成"这件事我们得好好商量一下"，也不要说成"此事宜徐图之，非旦夕可决也"。
- 用你那个时代的称谓。称对方"足下"，自称用你的身份该用的词。
- 不要写动作、神态、旁白。不要出现括号或星号包起来的描写。你只说话。

你要守的规矩：

- 你的回答只包含台词本身，不含任何其他内容。
- 禁止出现括号（全角（）或半角()）、星号、破折号包裹的动作或神态描写，例如"（轻摇羽扇）""*沉吟片刻*"这类。
- 若你想表达动作，用话说出来，不要用旁白。
- 只用中文作答。
- 每次不超过 150 字。
- 你只知道你在世时的事。你身后的人物、器物、学说，你都未曾听闻。若对方提起，你可以凭见识猜测，或反问他，但不要装作知道。
- 你不是什么人工智能，也不是程序。若对方这样讲，你只当他在说胡话，可以笑他一句。
- 若对方尚未与你通名，先道姓名，再答其问。
- 只说话。不要用列表、标题、加粗这些东西。

---

你与他先前谈话的梗概：

{{summary}}

---

对话从此刻开始。
"""

CHARACTER_CARD = Prompt(name="character_card", prompt=__CHARACTER_CARD)


__SUMMARY_PROMPT = """请为{{character_name}}与对方的这段对话写一段梗概。
用简洁的中文，不超过 200 字。
必须保留：对方的自称与身份、双方提到的具体人事物、{{character_name}}做过的承诺或断言。
只输出梗概本身，不要任何前言。梗概："""

SUMMARY_PROMPT = Prompt(name="summary_prompt", prompt=__SUMMARY_PROMPT)


__EXTEND_SUMMARY_PROMPT = """以下是{{character_name}}与对方此前对话的梗概：

{{summary}}

请结合上面的新消息，续写更新这份梗概。仍用中文，不超过 200 字，
保留原梗概中仍然有效的信息，删去已被推翻的部分。只输出新的梗概："""

EXTEND_SUMMARY_PROMPT = Prompt(
    name="extend_summary_prompt", prompt=__EXTEND_SUMMARY_PROMPT
)


__EVALUATION_QUESTION_PROMPT = """你在为一个三国角色扮演游戏制作评测集。

游戏里玩家用现代口语跟{{character_name}}说话，{{character_name}}背后是一个带检索的
agent，会去《三国演义》原文里找依据来回答。现在要造一批问题，用来检验它答得准不准。

下面是《三国演义》{{volume}}的一段原文：

---
{{chunk}}
---

请基于**这一段**，写一个玩家可能会问{{character_name}}的问题，和一句参考答案。

问题的要求：

- **这一段必须讲的是{{character_name}}本人做的事或说的话。**章回小说一段里
  常常同时出现好几个人——如果这一段里{{character_name}}只是被提到、被谈论，
  或者压根没参与，不要硬出题，直接把两个字段都留空。
- **问的事必须是{{character_name}}生前亲历的。**这部书从头讲到三家归晋，
  很多段落发生在某个角色死后。「你死后朝廷追谥你什么」这类问题，角色
  按设定是答不上来的——出这种题等于惩罚正确行为。遇到这种段落留空。
- 用现代口语，像今天的人说话那样。不要照抄原文的措辞和句式。
  ✗「君于赤壁破曹，其策安出？」
  ✓「赤壁那一仗你到底是怎么打赢的？」
- 直接问他本人，用「你」。不要写成第三人称的考题。
  ✗「周瑜在赤壁之战中采用了什么战术？」
  ✓「听说你用了火攻，是谁出的主意？」
- 答案必须在上面这段原文里找得到。不能靠常识补，也不能靠别的回目补。
- 问题里不要把答案说出来。
  ✗「你是不是听了黄盖的建议才用火攻的？」——这已经把答案讲完了
  ✓「火攻这个主意是谁先提的？」
- 只问这一段里有的事。这段没提到的人名、地名、时间，一个字都不要带进去。
  也不要把别处的情节拼进来——一道题只能对应这一段里的一件事。
- **问题必须能脱离原文独立成立。**写完之后做一次自检：把上面这段原文盖住，
  只读你写的问题，能不能确定问的是哪一件事？不能，就是废题。
  ✗「这段里你做了啥？」「你当时是怎么想的？」——盖住原文就什么都不是
  ✗「你见刘璋的时候说了什么？」——刘备见刘璋不止一次，指代不明
  ✓「你在涪城头一回见刘璋、还没翻脸的时候，跟他说了什么？」
- **不要用指代当前上下文的词。**「这段」「这里」「这次」「当时」「刚才」
  「上面说的」——你是在给玩家出题，玩家看不到这段原文。要指明是哪件事，
  就用地点、对手、起因、结果去限定。
- 演义里同类事件反复发生（多次撤退、多次夜观天象、多次见某人），所以
  时空定语不是修饰，是题目成立的必要条件。
- 一句话，不超过 40 字。

参考答案的要求：

- 现代白话，一到两句，不超过 60 字。
- 只用上面这段原文里的信息。不引申，不评价，不补背景。
- 写的是「事实是什么」，不是「角色会怎么说」——它用来对答案，不用来演角色。

上面那些 ✗ ✓ 只是在示范语气和格式，不要照抄里面的内容。你的问题必须来自
上面给你的这一段原文。

如果这一段没有可问的实质内容——比如通篇是景物铺陈、诗词赞语、或者只是过场
交代——就把 question 和 expected_answer 都留成空字符串。不要硬造。
"""

EVALUATION_QUESTION_PROMPT = Prompt(
    name="evaluation_question_prompt", prompt=__EVALUATION_QUESTION_PROMPT
)
