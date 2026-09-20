from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

Splitter = RecursiveCharacterTextSplitter


def get_splitter(chunk_size: int) -> Splitter:
    chunk_overlap = int(0.15 * chunk_size)

    logger.info(
        f"Getting splitter with chunk size: {chunk_size} and overlap: {chunk_overlap}"
    )

    return RecursiveCharacterTextSplitter(
        separators=["\n", "也", "矣", "焉", "耳", "乎", "曰", ""],
        keep_separator="end",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
