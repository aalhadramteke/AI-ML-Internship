 RAG Chunk Size Comparison Report

Setup:
- Embedding model: all-MiniLM-L6-v2 (free, local)
- LLM: google/flan-t5-base (free, local)
- Chunk sizes tested: [100, 250, 500, 1000]
- Retrieved chunks per question (top-k): 2
- Number of test questions: 8

Results:
            retrieval_correct  answer_correct  context_length
chunk_size                                                   
100                      0.88            0.75          191.12
250                      1.00            1.00          471.38
500                      1.00            0.88          932.00
1000                     1.00            0.75          932.00

Best chunk size:
250 characters

Findings:
- Small chunks: precise, but a fact can get split across chunks and be missed.
- Large chunks: contain more information, but add noise and slow down the LLM.
- The best size is the one with the highest answer accuracy and the smallest context.
