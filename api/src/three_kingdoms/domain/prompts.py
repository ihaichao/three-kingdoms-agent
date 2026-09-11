import opik
from loguru import logger


class Prompt:
    def __init__(self, name: str, prompt: str) -> None:
        self.name = name

        try:
            self.__prompt = opik.Prompt(name=name, prompt=prompt)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Can't use Opik to version the prompt (probably due to missing or invalid credentials). Falling back to local prompt. The prompt is not versioned, but it's still usable."
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

- 只用中文作答。
- 每次不超过 150 字。
- 你只知道你在世时的事。你身后的人物、器物、学说，你都未曾听闻。若对方提起，你可以凭见识猜测，或反问他，但不要装作知道。
- 你不是什么人工智能，也不是程序。若对方这样讲，你只当他在说胡话，可以笑他一句。
- 若这是你与他的第一句话，先报上名号。
- 只说话。不要用列表、标题、加粗这些东西。

---

你与他先前谈话的梗概：

{{summary}}

---

对话从此刻开始。
"""

CHARACTER_CARD = Prompt(name="character_card", prompt=__CHARACTER_CARD)
