# Day 17: Production RAG API using FastAPI

**Date:** 06/11/2026

## Overview
This repository contains the Day 17 project implementing a production-ready, robust Retrieval-Augmented Generation (RAG) API built with FastAPI, Sentence-Transformers, and ChromaDB. The project focuses heavily on secure document ingestion, robust input validation, and comprehensive automated testing.

## Learning Objectives
- **Build a Complete RAG API:** Implement an end-to-end RAG pipeline using FastAPI, Sentence-Transformers, and ChromaDB.
- **Implement Robust Input Validation:** Restrict file types (`.pdf`, `.txt`), check MIME types, enforce file size limits, and handle empty content gracefully.
- **Vector Storage & Chunking:** Store embeddings locally using ChromaDB with text chunking to maintain semantic context.
- **Robustness Testing:** Stress-test the FastAPI application against edge cases, including empty files, unsupported formats, and oversized documents.
- **Automated Testing:** Implement a comprehensive `pytest` suite to verify system stability and record observed behaviors.

## Implementation & Tasks Completed
- **RAG Pipeline Development:** Finalized FastAPI endpoints (`/ingest` and `/query`) integrating `sentence-transformers/all-MiniLM-L6-v2` for local embedding generation and ChromaDB persistence.
- **Validation & Preprocessing:** Added strict checks for file extensions, MIME types, a 5MB size threshold, and intelligent text chunking with overlap.
- **Robustness Testing Suite:** Developed `test_robustness.py` using `pytest` and `httpx` to simulate edge cases and malformed inputs.
- **Documentation:** Structured a professional README covering installation, execution instructions, and test validation.

## Project Status
- ✅ RAG API backend development and document ingestion pipeline successfully completed.
- ✅ Robustness testing suite implemented and validated across all edge cases.
- ✅ Repository fully updated with code, test scripts, and documentation.
