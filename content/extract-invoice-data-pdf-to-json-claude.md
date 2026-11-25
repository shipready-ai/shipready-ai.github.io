---
title: Extract invoice data from PDF to JSON with Claude (Python)
description: Turn invoice PDFs and phone photos into validated JSON with Claude structured outputs and a Pydantic schema. No OCR library and no template per vendor. Includes cost per document.
kit: docsift
date: 2026-11-25
---

Typing invoices into a spreadsheet or accounting system is slow, boring and error-prone. Old-style automation needed an OCR engine plus a template for every vendor's layout, and broke whenever a vendor changed theirs. A modern vision-capable model reads invoices the way a person does: any layout, scanned or digital, any language.

This guide builds an invoice extractor in one Python file. You give it a PDF or a photo; it gives back JSON that always matches your schema. The finished code is free on GitHub: [claude-invoice-extraction](https://github.com/{{owner}}/claude-invoice-extraction).

## Step 1: describe the data you want with Pydantic

```python
from pydantic import BaseModel, Field

class LineItem(BaseModel):
    description: str
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None

class Invoice(BaseModel):
    vendor_name: str | None = Field(description="Who issued the invoice")
    customer_name: str | None = Field(description="Who the invoice is billed to")
    invoice_number: str | None = None
    invoice_date: str | None = Field(description="YYYY-MM-DD")
    due_date: str | None = Field(description="YYYY-MM-DD")
    currency: str | None = Field(description="ISO code such as USD, EUR, VND")
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None
    line_items: list[LineItem] = []
```

Every field is optional on purpose. If a due date isn't printed, you want `null`, not a guess.

## Step 2: send the file

PDFs go to Claude as a `document` block, images as an `image` block, both base64-encoded:

```python
data = base64.standard_b64encode(path.read_bytes()).decode()
block = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}}
```

Claude reads each PDF page as both text and an image, so scanned invoices and photos work too.

## Step 3: ask for structured output

```python
response = client.beta.messages.parse(
    model="claude-opus-5-5",
    max_tokens=16000,
    system=SYSTEM,
    messages=[{"role": "user", "content": [block, {"type": "text", "text": "Fill in the invoice fields."}]}],
    output_format=Invoice,
    output_config={"effort": "low"},
)
invoice = response.parsed_output   # an Invoice object, already validated
```

`output_format=Invoice` turns your Pydantic model into a JSON schema and **constrains Claude's answer to it**. You never write a regex over the reply or retry because a bracket was missing.

## Step 4: a prompt that says "copy, don't guess"

```
You copy details from invoices into fields, exactly as printed.
- Copy, do not guess. If a field is not on the document, use null.
- Numbers are plain numbers with no currency signs or thousands separators.
- Dates are YYYY-MM-DD.
- List every line item in order, including discounts as negative amounts.
```

For other countries, add the local rules. For Vietnamese invoices, for example, "1.234.567" means 1234567 and dates are day first.

## The result

```json
{
  "vendor_name": "Northwind Design Studio",
  "invoice_number": "NW-2026-0117",
  "invoice_date": "2026-02-12",
  "currency": "USD",
  "subtotal": 2070.0,
  "tax": 186.3,
  "total": 2256.3,
  "line_items": [
    {"description": "Logo design, 3 concepts", "quantity": 1, "unit_price": 1200.0, "amount": 1200.0},
    {"description": "Brand guidelines (hours)", "quantity": 6, "unit_price": 95.0, "amount": 570.0}
  ]
}
```

Run many files at once with `python extract.py invoices/*.pdf --out results.jsonl`.

## What it costs

A one-page invoice costs roughly 1 to 3 US cents with `claude-opus-5-5` at low effort. For a business processing 500 invoices a month, that's under $15 in model costs, against hours of manual typing.

## From a script to a tool a team trusts

Extraction is the easy part. Teams that process invoices every day also need:

1. **Checks.** Do the line items add up to the subtotal? Does subtotal plus tax equal the total? Is the tax ID valid? Anything that fails goes to a person.
2. **Uncertain fields.** Blurry or handwritten values flagged, so the reviewer looks only where it matters.
3. **A review screen.** The document on one side, editable fields on the other, approve with one click.
4. **More document types.** Receipts, Vietnamese VAT invoices (hóa đơn GTGT), and your own.
5. **Exports and integrations.** CSV and Excel for the accountant, a webhook into the accounting system on approval.
6. **A queue**, so 200 uploads at month end don't time out, plus a cost log and a daily spend cap.

## Get the full kit

**[DocSift: Document Extraction Kit]({{kit_url}})** ({{kit_price}}) is that whole app: upload and queue, side-by-side review, total checks and uncertain-field flags, invoice, receipt and Vietnamese VAT invoice types (add your own in one file), CSV and Excel export, webhooks, passwords, a cost log, and a one-command AWS deploy. Measured cost: about 3 cents per document.

Or start free with the [one-file extractor on GitHub](https://github.com/{{owner}}/claude-invoice-extraction).
