"""LLM completion and RAG prompt templates."""

from src.generation.config import GenerationConfig
from src.generation.llm_client import generate_rag_answer

__all__ = ["GenerationConfig", "generate_rag_answer"]
