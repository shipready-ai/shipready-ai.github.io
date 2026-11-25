---
title: Build a PDF chatbot with citations using Claude and LangChain (RAG)
description: A retrieval-augmented generation (RAG) chatbot that answers questions about your PDFs and cites the exact page for every statement. FastAPI, LangChain, ChromaDB, local embeddings and Claude, step by step.
kit: docchat
date: 2026-11-25
---

"Chat with your PDFs" is the most requested AI feature in companies: employee handbooks, contracts, product manuals, policies. A chatbot that answers confidently but wrongly is worse than none, though. The answer has to **show where it came from**, so people can check it.

This guide walks through a retrieval-augmented generation (RAG) chatbot where every statement carries a citation like `[1]` that opens the exact passage, file and page. The finished code is free on GitHub: [rag-document-chatbot](https://github.com/{{owner}}/rag-document-chatbot) (FastAPI backend, Next.js UI, Docker Compose).

## How RAG works, in four steps

1. **Ingest.** Extract the text of each PDF page, split it into chunks, turn each chunk into an embedding vector, store the vectors.
2. **Retrieve.** For a question, embed it the same way and find the closest chunks.
3. **Answer.** Send Claude the question plus those chunks, numbered, with instructions to answer only from them and cite the numbers.
4. **Show.** Stream the answer to the browser and turn each `[n]` into a link to its source.

## Step 1: page-aware chunking

```python
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
for page_number, page in enumerate(PdfReader(path).pages, start=1):
    for chunk in splitter.split_text(page.extract_text() or ""):
        docs.append(Document(page_content=chunk, metadata={"filename": name, "page": page_number}))
```

Split **per page**, not per document, and keep the page number in the metadata. That's what makes "page 12" citations possible.

## Step 2: local embeddings, no extra API key

```python
from fastembed import TextEmbedding
model = TextEmbedding("BAAI/bge-small-en-v1.5")
```

FastEmbed runs a small embedding model on the CPU, so ingest costs nothing per page and needs no second API key. The vectors go into ChromaDB with cosine distance.

## Step 3: retrieve and number the sources

```python
results = store.similarity_search_with_score(question, k=5)
sources = "\n".join(
    f'<source number="{i}" file="{doc.metadata["filename"]}" page="{doc.metadata["page"]}">\n{doc.page_content}\n</source>'
    for i, (doc, _) in enumerate(results, start=1)
)
```

## Step 4: a prompt that forces grounding

```
You answer questions using only the document excerpts provided in <sources>.
- Base every statement on the sources. If they do not contain the answer, say you could not find it
  in the uploaded documents and suggest what to upload or ask instead.
- Cite sources inline with their number in square brackets, like [1] or [2][3], right after the
  statement they support.
- Answer in the same language as the question.
```

"Say you could not find it" is the most important line. Without it, the model fills gaps from general knowledge, and users can't tell which parts came from their documents.

## Step 5: stream it

```python
async with client.messages.stream(model="claude-opus-5-5", system=SYSTEM_PROMPT,
                                  messages=messages, max_tokens=4000) as stream:
    async for text in stream.text_stream:
        yield f"data: {json.dumps({'type': 'token', 'text': text})}\n\n"
```

Send the sources first as a Server-Sent Event, then the tokens. The UI can render citation links the moment `[1]` appears.

## What changes in production

The demo works on a laptop. Putting it in front of a company's staff or a client's customers adds:

1. **Access control.** An admin password for uploads and an access password (or sign-in) for readers.
2. **Cost control.** A per-IP rate limit and a **daily spend cap**, so one curious user or a bot can't run up the bill, plus a cost log so you can price it for clients (about $10 per 1,000 questions with Claude Opus measured).
3. **HTTPS** and a production Docker setup.
4. **Backups and restores** of the vector store and uploaded files.
5. **A repeatable deploy** and a check that it works after each deploy.

## Get the full kit

The **[AWS Document Chatbot Starter Kit]({{kit_url}})** ({{kit_price}}) adds all of that to this project: admin and access passwords, rate limit, daily spend cap and `/usage` report, Caddy HTTPS, backup and restore scripts, a deploy check, a cost sheet, and a one-command AWS deploy (with a free HTTPS name when you don't have a domain yet).

Or start free with the [open-source chatbot on GitHub](https://github.com/{{owner}}/rag-document-chatbot).
