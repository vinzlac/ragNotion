"""Tests unitaires shared (config, schémas)."""
import pytest
from shared.config import RAGPipelineSettings, get_rag_settings
from shared.schemas import ChatSource, ChatResponse


def test_rag_settings_defaults():
    settings = RAGPipelineSettings()
    assert settings.chunk_size == 512
    assert settings.top_k == 20
    assert settings.top_n == 5


def test_chat_response_schema():
    r = ChatResponse(answer="Oui.", sources=[], rag_version="v1")
    assert r.answer == "Oui."
    assert r.rag_version == "v1"


def test_chat_source_schema():
    s = ChatSource(page_id="abc", title="Page", url="https://notion.so/abc", snippet="Extrait...")
    assert s.page_id == "abc"
    assert s.title == "Page"
