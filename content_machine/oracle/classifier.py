"""Topic classification taxonomy for developer and engineering content."""

from __future__ import annotations

import re
from typing import Optional

TOPIC_SYSTEMS = "⚡ Systems & Architecture"
TOPIC_LEADERSHIP = "📈 Engineering Leadership"
TOPIC_AI = "🤖 AI & Machine Learning"
TOPIC_CLOUD = "☁️ Cloud & Infrastructure"
TOPIC_SECURITY = "🔒 Security & Reliability"
TOPIC_DEVTOOLS = "🛠️ Developer Productivity"
TOPIC_GENERAL = "💻 General Engineering"

ALL_TOPICS = [
    TOPIC_SYSTEMS,
    TOPIC_LEADERSHIP,
    TOPIC_AI,
    TOPIC_CLOUD,
    TOPIC_SECURITY,
    TOPIC_DEVTOOLS,
    TOPIC_GENERAL,
]

_PATTERNS = [
    (
        TOPIC_AI,
        re.compile(
            r"\b(llm|llms|transformer|transformers|lora|pytorch|fine-tuning|fine-tune|"
            r"speculative decoding|kv cache|gpu|gpus|cuda|inference|weights|deep learning|"
            r"neural net|diffusion|rag|vector db|embeddings|prompt engineering|"
            r"openai|anthropic|mistral|deepseek|hugging face|huggingface|langchain)\b",
            re.IGNORECASE,
        ),
    ),
    (
        TOPIC_SECURITY,
        re.compile(
            r"\b(cve|vulnerability|vulnerabilities|backdoor|supply chain attack|"
            r"supply chain attacks|zero-day|zeroday|openssl|tls handshake|webauthn|"
            r"passkeys|oauth|encryption|cryptography|exploit|malware|ransomware|"
            r"ddos|hardening authentication|security breach|infosec)\b",
            re.IGNORECASE,
        ),
    ),
    (
        TOPIC_LEADERSHIP,
        re.compile(
            r"\b(engineering org|scaling an engineering|staff engineer|principal engineer|"
            r"engineering manager|engineering management|team velocity|career ladder|"
            r"career ladders|engineering throughput|10x engineer|hiring developers|"
            r"mentorship|tech lead|engineering leadership|developer retention)\b",
            re.IGNORECASE,
        ),
    ),
    (
        TOPIC_DEVTOOLS,
        re.compile(
            r"\b(turborepo|monorepo|ci build|ci/cd|git internals|plumbing commands|"
            r"dag traversal|vite|eslint|webpack|compiler|developer tooling|"
            r"developer productivity|developer experience|dx|code review|refactoring|"
            r"unit test|testing strategy|linting|package manager)\b",
            re.IGNORECASE,
        ),
    ),
    (
        TOPIC_SYSTEMS,
        re.compile(
            r"\b(ebpf|linux kernel|memory alloc|memory allocator|rust|c\+\+|cpu cache|"
            r"low-level|tcp socket|socket buffer|socket buffers|latency|concurrency|"
            r"io_uring|raft|paxos|consensus|operating system|assembly|x86|arm64|"
            r"garbage collection|memory management|dns cache|cache storage|petabytes|terabytes of memory)\b",
            re.IGNORECASE,
        ),
    ),
    (
        TOPIC_CLOUD,
        re.compile(
            r"\b(kubernetes|k8s|eks|gke|docker|container|microservices|postgres|"
            r"postgresql|connection pooling|database|dynamodb|spanner|mongodb|"
            r"redis|outage postmortem|sre|aws|gcp|azure|cloudflare|load balancer|"
            r"kafka|rabbitmq|terraform|serverless|scalability)\b",
            re.IGNORECASE,
        ),
    ),
]


def classify_content_topic(title: str, body: str = "", source: str = "") -> str:
    """Classify technical content into one of the 6 core engineering taxonomies."""
    text = f"{title} {body}".strip()
    if not text:
        return TOPIC_GENERAL

    for topic, pattern in _PATTERNS:
        if pattern.search(text):
            return topic

    return TOPIC_GENERAL
