from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from three_kingdoms.config import settings

Splitter = RecursiveCharacterTextSplitter

# 《三国演义》：白话、有标点，按标点断句最自然。
_YANYI_SEPARATORS = ["\n", "。", "！", "？", "；", "，", ""]

# 《三国志》：文言、无标点，只能靠句末虚词找句子边界。
# 「曰」放在最后是因为它是句首标记不是句末，切在它前面会把说话人和话切开，
# 但总比按字数硬切强。
_ZHI_SEPARATORS = ["\n", "也", "矣", "焉", "耳", "乎", "曰", ""]


def get_splitter(chunk_size: int) -> Splitter:
    chunk_overlap = int(0.15 * chunk_size)
    separators = _YANYI_SEPARATORS if settings.CORPUS == "yanyi" else _ZHI_SEPARATORS

    logger.info(
        f"Getting splitter with chunk size: {chunk_size}, "
        f"overlap: {chunk_overlap}, corpus: {settings.CORPUS}"
    )

    return RecursiveCharacterTextSplitter(
        separators=separators,
        keep_separator="end",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
