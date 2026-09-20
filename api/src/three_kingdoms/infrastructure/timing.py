"""耗时测量的小工具。

只在排查性能时用。它不做采样、不聚合、不上报——就是打日志。
真要做可观测性，模块 4 会接 Opik 的 tracing，那时这个文件可以删掉。
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager

from loguru import logger


@contextmanager
def timed(label: str) -> Iterator[None]:
    """测量一段代码的耗时并打日志。

        with timed("LLM 调用"):
            ...

    同步和异步代码里都能用——它自己不 await，只是在进出时各记一个时间点，
    中间挂起多久都算得上。

    用 time.perf_counter() 而不是 time.time()：前者是单调时钟，
    不受系统时间调整影响，测时间差就该用它。
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        logger.info(f"[耗时] {label}: {time.perf_counter() - start:.2f}s")
