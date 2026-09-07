import pytest
from content_machine.oracle.classifier import (
    classify_content_topic,
    TOPIC_SYSTEMS,
    TOPIC_LEADERSHIP,
    TOPIC_AI,
    TOPIC_CLOUD,
    TOPIC_SECURITY,
    TOPIC_DEVTOOLS,
    TOPIC_GENERAL,
)


def test_classify_systems_architecture():
    title = "Memory Allocation in the Linux Kernel with eBPF"
    assert classify_content_topic(title) == TOPIC_SYSTEMS

    title2 = "Writing a Custom Memory Allocator in Rust"
    assert classify_content_topic(title2) == TOPIC_SYSTEMS

    title3 = "Understanding TCP socket buffers and latency"
    assert classify_content_topic(title3) == TOPIC_SYSTEMS


def test_classify_engineering_leadership():
    title = "Scaling an Engineering Org from 10 to 100 Developers"
    assert classify_content_topic(title) == TOPIC_LEADERSHIP

    title2 = "Staff Engineer Archetypes and Career Ladders"
    assert classify_content_topic(title2) == TOPIC_LEADERSHIP

    title3 = "How We Measure Team Velocity and Engineering Throughput"
    assert classify_content_topic(title3) == TOPIC_LEADERSHIP


def test_classify_ai_machine_learning():
    title = "Fine-Tuning Llama 3 with LoRA and PyTorch"
    assert classify_content_topic(title) == TOPIC_AI

    title2 = "Speculative Decoding and KV Cache Compression in LLMs"
    assert classify_content_topic(title2) == TOPIC_AI

    title3 = "GPU Cluster Architecture for Distributed Transformer Training"
    assert classify_content_topic(title3) == TOPIC_AI


def test_classify_cloud_infrastructure():
    title = "Kubernetes Pod Autoscaling at Scale in AWS EKS"
    assert classify_content_topic(title) == TOPIC_CLOUD

    title2 = "Postgres Connection Pooling and Microservices Outage Postmortem"
    assert classify_content_topic(title2) == TOPIC_CLOUD

    title3 = "Migrating 50TB from DynamoDB to Spanner"
    assert classify_content_topic(title3) == TOPIC_CLOUD


def test_classify_security_reliability():
    title = "Analysis of the XZ Utils Backdoor and Supply Chain Attacks"
    assert classify_content_topic(title) == TOPIC_SECURITY

    title2 = "Zero-Day Vulnerability in OpenSSL TLS Handshake"
    assert classify_content_topic(title2) == TOPIC_SECURITY

    title3 = "Hardening Authentication with WebAuthn and Passkeys"
    assert classify_content_topic(title3) == TOPIC_SECURITY


def test_classify_devtools_productivity():
    title = "How Turborepo Reduced Our Monorepo CI Build Time by 70%"
    assert classify_content_topic(title) == TOPIC_DEVTOOLS

    title2 = "Git Internals: Plumbing Commands and DAG Traversal"
    assert classify_content_topic(title2) == TOPIC_DEVTOOLS

    title3 = "Modern Developer Tooling with Vite and ESLint v9"
    assert classify_content_topic(title3) == TOPIC_DEVTOOLS


def test_classify_fallback_general():
    title = "Random Thoughts on a Rainy Tuesday Afternoon"
    assert classify_content_topic(title) == TOPIC_GENERAL
