"""Tool Calling helpers — plug Schift search/chat into any LLM agent.

Usage::

    from schift import Schift

    client = Schift(api_key="sch_xxx")

    # OpenAI
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "계약서에서 해지 조건?"}],
        tools=client.tools.openai(),
    )
    result = client.tools.handle(response.choices[0].message.tool_calls[0])

    # Claude
    response = anthropic.messages.create(
        model="claude-sonnet-4-20250514",
        tools=client.tools.anthropic(),
        messages=[{"role": "user", "content": "인보이스 총액?"}],
    )
    result = client.tools.handle(response.content[0])

    # LangChain
    tools = client.tools.langchain()
"""

from __future__ import annotations

import json
from typing import Any, Callable, Optional


class SchiftTools:
    """Generate tool definitions and handle tool calls for Schift search/chat."""

    def __init__(
        self,
        search_fn: Callable[..., Any],
        chat_fn: Callable[..., Any],
        collection: str = "",
        bucket_id: str = "",
        top_k: int = 5,
        include_chat: bool = False,
        prefix: str = "schift",
    ):
        self._search_fn = search_fn
        self._chat_fn = chat_fn
        self._collection = collection
        self._bucket_id = bucket_id
        self._top_k = top_k
        self._include_chat = include_chat
        self._prefix = prefix

    # ---- OpenAI format ----

    def openai(self) -> list[dict]:
        """Return tool definitions in OpenAI function calling format."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": f"{self._prefix}_search",
                    "description": (
                        "Search through uploaded company documents. "
                        "Returns relevant text passages with source citations and relevance scores."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query in natural language",
                            },
                            "collection": {
                                "type": "string",
                                "description": "Document collection to search in",
                            },
                            "top_k": {
                                "type": "number",
                                "description": "Number of results to return (default 5)",
                            },
                        },
                        "required": ["query"],
                    },
                },
            }
        ]

        if self._include_chat:
            tools.append({
                "type": "function",
                "function": {
                    "name": f"{self._prefix}_chat",
                    "description": (
                        "Ask a question about uploaded documents and get an "
                        "AI-generated answer with source citations."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "The question to ask",
                            },
                            "bucket_id": {
                                "type": "string",
                                "description": "Document bucket to search in",
                            },
                        },
                        "required": ["message"],
                    },
                },
            })

        return tools

    # ---- Anthropic (Claude) format ----

    def anthropic(self) -> list[dict]:
        """Return tool definitions in Anthropic/Claude format."""
        tools = [
            {
                "name": f"{self._prefix}_search",
                "description": (
                    "Search through uploaded company documents. "
                    "Returns relevant text passages with source citations and relevance scores."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query in natural language",
                        },
                        "collection": {
                            "type": "string",
                            "description": "Document collection to search in",
                        },
                        "top_k": {
                            "type": "number",
                            "description": "Number of results to return (default 5)",
                        },
                    },
                    "required": ["query"],
                },
            }
        ]

        if self._include_chat:
            tools.append({
                "name": f"{self._prefix}_chat",
                "description": (
                    "Ask a question about uploaded documents and get an "
                    "AI-generated answer with source citations."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The question to ask",
                        },
                        "bucket_id": {
                            "type": "string",
                            "description": "Document bucket to search in",
                        },
                    },
                    "required": ["message"],
                },
            })

        return tools

    # ---- LangChain format ----

    def langchain(self):
        """Return LangChain Tool objects (requires langchain-core installed)."""
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel, Field

        class SearchInput(BaseModel):
            query: str = Field(description="Search query in natural language")
            collection: str = Field(default="", description="Collection name")
            top_k: int = Field(default=5, description="Number of results")

        def _search(query: str, collection: str = "", top_k: int = 5) -> str:
            results = self._exec_search(query=query, collection=collection, top_k=top_k)
            return json.dumps(results, ensure_ascii=False)

        tools = [
            StructuredTool.from_function(
                func=_search,
                name=f"{self._prefix}_search",
                description="Search through uploaded company documents",
                args_schema=SearchInput,
            )
        ]

        if self._include_chat:
            class ChatInput(BaseModel):
                message: str = Field(description="Question to ask")
                bucket_id: str = Field(default="", description="Bucket ID")

            def _chat(message: str, bucket_id: str = "") -> str:
                result = self._exec_chat(message=message, bucket_id=bucket_id)
                return json.dumps(result, ensure_ascii=False)

            tools.append(
                StructuredTool.from_function(
                    func=_chat,
                    name=f"{self._prefix}_chat",
                    description="Ask a question about uploaded documents",
                    args_schema=ChatInput,
                )
            )

        return tools

    # ---- Universal handler ----

    def handle(self, tool_call: Any) -> str:
        """Handle a tool call from any provider. Auto-detects format.

        Supports:
            - OpenAI: tool_call.function.name / tool_call.function.arguments
            - Anthropic: tool_call.name / tool_call.input
            - Raw dict: {"name": ..., "input": ...}
        """
        name: str
        args: dict

        # OpenAI format (object with .function)
        if hasattr(tool_call, "function"):
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
        # Anthropic format (object with .type == "tool_use")
        elif hasattr(tool_call, "type") and getattr(tool_call, "type", "") == "tool_use":
            name = tool_call.name
            args = tool_call.input or {}
        # Dict format
        elif isinstance(tool_call, dict):
            name = tool_call.get("name", tool_call.get("function", {}).get("name", ""))
            args = tool_call.get("input", {})
            if not args and "function" in tool_call:
                args = json.loads(tool_call["function"].get("arguments", "{}"))
        else:
            raise ValueError(f"Unrecognized tool call format: {type(tool_call)}")

        if name == f"{self._prefix}_search":
            results = self._exec_search(**args)
            return json.dumps(results, ensure_ascii=False)

        if name == f"{self._prefix}_chat":
            result = self._exec_chat(**args)
            return json.dumps(result, ensure_ascii=False)

        raise ValueError(f"Unknown tool: {name}")

    # ---- Internal ----

    def _exec_search(self, query: str, collection: str = "", top_k: int = 0, **_) -> list[dict]:
        return self._search_fn(
            query=query,
            collection=collection or self._collection,
            top_k=top_k or self._top_k,
        )

    def _exec_chat(self, message: str, bucket_id: str = "", **_) -> dict:
        resp = self._chat_fn(
            bucket_id=bucket_id or self._bucket_id,
            message=message,
        )
        if hasattr(resp, "__dict__"):
            return {
                "reply": resp.reply,
                "sources": [{"id": s.id, "score": s.score, "text": s.text} for s in resp.sources],
                "model": resp.model,
            }
        return resp
