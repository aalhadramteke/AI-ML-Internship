# Day 16: Vector Databases & RAG (Retrieval-Augmented Generation)

> **Date:** November 5, 2026
>
> **Topic:** Building, Evaluating, and Benchmarking a Local RAG System

## Overview

This project implements a complete, end-to-end Retrieval-Augmented Generation (RAG) pipeline running locally using open-source models. The primary goal of this experiment is to evaluate the impact of **document chunk sizes** (100, 250, 500, and 1000 characters) on vector retrieval accuracy, LLM answer generation correctness, and context length efficiency.

## Objectives & Tasks

* **Local RAG Pipeline:** Build an end-to-end RAG system utilizing open-source embedding and language models.

* **Chunking Experiment:** Preprocess and slice knowledge base documents across multiple character chunk sizes ([100, 250, 500, 1000]).

* **Vector Search Engine:** Construct a semantic retrieval engine using normalized embeddings (`all-MiniLM-L6-v2`) and cosine similarity matrix operations.

* **LLM Integration:** Connect the vector search retriever to a local generator model (`google/flan-t5-base`) to produce grounded answers.

* **System Evaluation:** Design a benchmark test suite (8 question/keyword pairs) to measure both **Retrieval Accuracy** and **Answer Accuracy**.

* **Data & Visual Analytics:** Export evaluation metrics to CSV tables, generate visual comparison charts, and compile a final markdown report.

## Implementation & Architecture

### 1. Stack & Dependencies

* **Language Models:** `google/flan-t5-base` (Text Generation), `all-MiniLM-L6-v2` (Sentence Embeddings)

* **Core Libraries:** `transformers`, `sentence-transformers`, `torch`, `pandas`, `numpy`, `matplotlib`

### 2. Workflow Breakdown

1. **Document Ingestion & Chunking:** Loaded internal documentation (`hr_policy`, `product_faq`) and split text dynamically into character slices via `make_chunks()`.

2. **Indexing:** Generated normalized vector embeddings for each document chunk and indexed them into a vector space.

3. **Retrieval (`retrieve()`):** Query text is converted to a vector embedding to find the top-k (k=2) nearest chunk neighbors using matrix dot-product operations.

4. **Answer Generation (`ask()`):** Context chunks are combined with standard system prompts and fed into `google/flan-t5-base` to formulate brief, factual answers.

5. **Automated Evaluation:** Iterated through all chunk size variations and recorded performance metrics in a Pandas DataFrame (`evaluation_table`).

## Benchmark & Performance Summary

| Chunk Size (Chars) | Retrieval Accuracy | Answer Accuracy | Avg. Context Length (Chars) | Assessment | 
| ----- | ----- | ----- | ----- | ----- | 
| **100** | 88% (0.88) | 75% (0.75) | 191.12 | Context too narrow; key facts get split across boundaries. | 
| **250** | **100% (1.00)** | **100% (1.00)** | **471.38** | **Optimal balance of complete context and high accuracy.** | 
| **500** | 100% (1.00) | 88% (0.88) | 932.00 | Good retrieval, but larger context introduces slight noise. | 
| **1000** | 100% (1.00) | 75% (0.75) | 932.00 | Full context retained, but prompt dilution degrades LLM output quality. | 

### Key Findings

* **Optimal Choice:** **250 characters** was identified as the optimal chunk size, achieving a **100% score in both retrieval and answer accuracy** while keeping prompt overhead minimal (471.38 characters).

* **Trade-off Insights:**

  * *Small chunks (100)* cause information loss across split boundaries.

  * *Large chunks (500-1000)* increase cost and token length while diluting relevant details, causing the LLM to hallucinate or misinterpret short factual questions.

## Repository Structure

```
.
├── rag_analysis.ipynb            # Primary Jupyter Notebook containing code & execution logs
├── response_evaluation_table.csv # Detailed evaluation log for all questions & chunk sizes
├── chunk_size_summary.csv        # Aggregated performance summary table
├── chunk_size_chart.png          # Visual performance bar chart (Accuracy vs Chunk Size)
├── comparison_report.md          # Executive markdown report of findings
└── README.md                     # Day 16 documentation

```

## Status

* \[x\] End-to-end local RAG pipeline implemented and tested.

* \[x\] Jupyter Notebook (`rag_analysis.ipynb`) completely executed with output logs.

* \[x\] Optimal chunk size (250 characters) identified and documented.

* \[x\] Evaluation data (`CSV`), visual plot (`PNG`), and report (`MD`) generated.

* \[x\] GitHub repository updated with all project deliverables.
