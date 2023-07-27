#!/usr/bin/env python3
import glob
import os
import shutil
from multiprocessing import Pool
from typing import List

from dotenv import load_dotenv
from langchain.docstore.document import Document
from langchain.document_loaders import (
    CSVLoader,
    EverNoteLoader,
    PDFMinerLoader,
    TextLoader,
    UnstructuredEmailLoader,
    UnstructuredEPubLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
    UnstructuredODTLoader,
    UnstructuredPowerPointLoader,
    UnstructuredWordDocumentLoader, )
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Milvus
from tqdm import tqdm

load_dotenv(".env")

MILVUS_HOST = os.environ.get('MILVUS_HOST')
MILVUS_PORT = os.environ.get('MILVUS_PORT')
source_directory = os.environ.get('SOURCE_DIRECTORY', 'source_documents')
KNOWLEDGE_FOLDER = os.environ.get('KNOWLEDGE_FOLDER')
KNOWLEDGE_FOLDER_BK = os.environ.get('KNOWLEDGE_FOLDER_BK')
chunk_size = 500
chunk_overlap = 50


# Custom document loaders
class MyElmLoader(UnstructuredEmailLoader):
    """在默认值不起作用时回退到文本纯"""

    def load(self) -> List[Document]:
        """EMl没有 html 使用text/plain"""
        try:
            try:
                doc = UnstructuredEmailLoader.load(self)
            except ValueError as e:
                if 'text/html content not found in email' in str(e):
                    # Try plain text
                    self.unstructured_kwargs["content_source"] = "text/plain"
                    doc = UnstructuredEmailLoader.load(self)
                else:
                    raise
        except Exception as e:
            # Add file_path to exception message
            raise type(e)(f"{self.file_path}: {e}") from e

        return doc


# 映射文件加载
LOADER_MAPPING = {
    ".csv": (CSVLoader, {}),
    # ".docx": (Docx2txtLoader, {}),
    ".doc": (UnstructuredWordDocumentLoader, {}),
    ".docx": (UnstructuredWordDocumentLoader, {}),
    ".enex": (EverNoteLoader, {}),
    ".eml": (MyElmLoader, {}),
    ".epub": (UnstructuredEPubLoader, {}),
    ".html": (UnstructuredHTMLLoader, {}),
    ".md": (UnstructuredMarkdownLoader, {}),
    ".odt": (UnstructuredODTLoader, {}),
    ".pdf": (PDFMinerLoader, {}),
    ".ppt": (UnstructuredPowerPointLoader, {}),
    ".pptx": (UnstructuredPowerPointLoader, {}),
    ".txt": (TextLoader, {"encoding": "utf8"}),
}


def load_single_document(file_path: str) -> List[Document]:
    ext = "." + file_path.rsplit(".", 1)[-1]
    if ext in LOADER_MAPPING:
        loader_class, loader_args = LOADER_MAPPING[ext]
        loader = loader_class(file_path, **loader_args)
        return loader.load()

    raise ValueError(f"文件不存在 '{ext}'")


def load_documents(source_dir: str, ignored_files: List[str] = []) -> List[Document]:
    """
    Loads all documents from the source documents directory, ignoring specified files
    """
    all_files = []
    for ext in LOADER_MAPPING:
        all_files.extend(

            glob.glob(os.path.join(source_dir, f"**/*{ext}"), recursive=True)
        )
    filtered_files = [file_path for file_path in all_files if file_path not in ignored_files]

    with Pool(processes=os.cpu_count()) as pool:
        results = []
        with tqdm(total=len(filtered_files), desc='Loading new documents', ncols=80) as pbar:
            for i, docs in enumerate(pool.imap_unordered(load_single_document, filtered_files)):
                results.extend(docs)
                pbar.update()

    return results


def load_documents_knowledge(source_dir: str, secondary_directories: str) -> List[Document]:
    """
    Loads all documents from the source documents directory, ignoring specified files
    """
    all_files = []
    for ext in LOADER_MAPPING:
        all_files.extend(

            glob.glob(os.path.join(source_dir, secondary_directories, f"**/*{ext}"), recursive=True)
        )
    filtered_files = [file_path for file_path in all_files if file_path]

    with Pool(processes=os.cpu_count()) as pool:
        results = []
        with tqdm(total=len(filtered_files), desc='Loading new documents', ncols=80) as pbar:
            for i, docs in enumerate(pool.imap_unordered(load_single_document, filtered_files)):
                results.extend(docs)
                pbar.update()

    return results


def process_documents(ignored_files: List[str] = []) -> List[Document]:
    """
    加载文档并拆分为块
    """
    print(f"加载文件目录: {source_directory}")
    documents = load_documents(source_directory, ignored_files)
    if not documents:
        print("没有文件需要加载")
        exit(0)
    print(f"加载 {len(documents)} 文件从 {source_directory}")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    texts = text_splitter.split_documents(documents)
    print(f"切割 {len(texts)} 文本块 (最大. {chunk_size} tokens 令牌)")
    return texts


def process_documents_knowledge(secondary_directories: str) -> List[Document]:
    """
    加载文档并拆分为块
    """
    print(f"加载文件目录: {KNOWLEDGE_FOLDER}")
    documents = load_documents_knowledge(KNOWLEDGE_FOLDER, secondary_directories)
    if not documents:
        print("没有文件需要加载")
        exit(0)
    print(f"加载 {len(documents)} 文件从 {KNOWLEDGE_FOLDER}")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    texts = text_splitter.split_documents(documents)
    print(f"切割 {len(texts)} 文本块 (最大. {chunk_size} tokens 令牌)")
    return texts


def does_vectorstore_exist(persist_directory: str) -> bool:
    """
    Checks if vectorstore exists
    """
    if os.path.exists(os.path.join(persist_directory, 'index')):
        if os.path.exists(os.path.join(persist_directory, 'chroma-collections.parquet')) and os.path.exists(
                os.path.join(persist_directory, 'chroma-embeddings.parquet')):
            list_index_files = glob.glob(os.path.join(persist_directory, 'index/*.bin'))
            list_index_files += glob.glob(os.path.join(persist_directory, 'index/*.pkl'))
            # At least 3 documents are needed in a working vectorstore
            if len(list_index_files) > 3:
                return True
    return False


def main(collection_name: str):
    # Create embeddings
    embeddings = OpenAIEmbeddings()

    texts = process_documents()

    vector_store = Milvus.from_documents(
        texts,
        collection_name=collection_name,
        embedding=embeddings,
        connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT}
    )


def main_knowledge(collection_name: str):
    # Create embeddings
    embeddings = OpenAIEmbeddings()

    texts = process_documents_knowledge(collection_name)

    Milvus.from_documents(
        texts,
        collection_name=collection_name,
        embedding=embeddings,
        connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT}
    )
    remove_file(os.path.join(KNOWLEDGE_FOLDER, collection_name), os.path.join(KNOWLEDGE_FOLDER_BK, collection_name))


def remove_file(old_path, new_path):
    print(old_path)
    print(new_path)
    filelist = os.listdir(old_path)  # 列出该目录下的所有文件,listdir返回的文件列表是不包含路径的。
    print(filelist)
    for file in filelist:
        src = os.path.join(old_path, file)
        dst = os.path.join(new_path, file)
        print('src:', src)  # 原文件路径下的文件
        print('dst:', dst)  # 移动到新的路径下的文件
        shutil.move(src, dst)


if __name__ == "__main__":
    main()
