# Conversation Mode Guide

Uh Bot now supports **interactive conversation mode** where you can upload a document once and then send multiple text commands for different types of analysis!

## Overview

### How It Works

```
1. You: /analyze
2. Bot: Shows welcome message
3. You: Upload document (PDF, DOCX, TXT, ZIP)
4. Bot: ✅ Document is ready!
5. You: Send text instruction ("Summarize", "Find risks", etc.)
6. Bot: Analyzes and sends result
7. You: Send another instruction for same document
8. Bot: Analyzes again with new instruction
... repeat until /cancel or clear document
```

## Quick Start

### Step 1: Start Analysis Mode

```
/analyze
```

Bot responds:

```
💬 Document Analysis Mode

Welcome to interactive document analysis!

How it works:
1️⃣ Upload a document (PDF, DOCX, TXT, or ZIP)
2️⃣ Bot confirms it's ready
3️⃣ Send text messages with analysis instructions
4️⃣ Bot analyzes based on your commands

Example:
You: [Upload contract.pdf]
Bot: Document ready! ✅
You: 'Identify all risks in this contract'
Bot: [Detailed risk analysis]

Ready? Upload your document or choose an action below.

📋 Upload Document | 📋 View Prompts
```

### Step 2: Upload Document

Click **"Upload Document"** button or directly send a file:

- **PDF** - Best for scanned documents
- **DOCX** - Microsoft Word documents
- **TXT** - Plain text files
- **ZIP** - Multiple files bundled

**Size limit:** 20 MB

Bot processes the file:

```
🔍 Processing document...
Downloading and extracting content...

✅ Document Ready!

File: contract.pdf
Size: 5,234 characters

Now send me instructions for analysis:

Examples:
📝 'Summarize this document'
📝 'Identify all risks'
📝 'Extract key points'
📝 'Analyze legal implications'

Or use a custom prompt with /prompts

🗑️ Clear Document | 📋 View Document Info
```

### Step 3: Send Analysis Instructions

Now send any text instruction for analyzing your document:

```
You: Summarize this document
Bot: 🤖 Analyzing 'contract.pdf'...
     📋 Instruction: Summarize this document

Bot: [Sends detailed summary]

You: What are the risks in this document?
Bot: 🤖 Analyzing 'contract.pdf'...
     📋 Instruction: What are the risks...

Bot: [Sends risk analysis]

You: Extract all dates and numbers
Bot: [Extracts data]
```

### Step 4: Keep Analyzing

Your document stays loaded in memory. Send as many instructions as you want:

```
You: Who are the parties involved?
Bot: [Lists parties]

You: Identify financial obligations
Bot: [Extracts financial info]

You: What are the termination clauses?
Bot: [Analyzes termination terms]
```

### Step 5: Clear When Done

Click **"Clear Document"** when you're done:

```
🗑️ Document cleared!

Ready for a new document. Upload one to get started.
```

Or start a new conversation with `/analyze` again.

---

## Command Reference

| Command | Function |
|---------|----------|
| `/analyze` | Start/reset conversation mode |
| `/prompts` | Manage custom analysis prompts |
| `/help` | Show general help |
| `/cancel` | Exit current operation |

## Supported File Formats

### Single Files

- **PDF** (.pdf) - Text extraction from PDFs
- **Word** (.docx) - Microsoft Word documents
- **Text** (.txt) - Plain text files
- **Images** (.png, .jpg) - OCR text extraction

### Archives

- **ZIP** (.zip) - Multiple files extracted and combined
- Supports mixed formats in ZIP

## Examples

### Example 1: Contract Review

```
You: /analyze
Bot: [Shows welcome]

You: [Upload contract.pdf]
Bot: ✅ Document Ready! (5,234 chars)

You: Identify all legal risks and obligations
Bot: [Detailed legal analysis]

You: What are the penalty clauses?
Bot: [Penalty analysis]

You: List all required signatures and dates
Bot: [Lists signatures and dates]

You: /cancel
Bot: [Session ends]
```

### Example 2: Research Paper Analysis

```
You: /analyze
Bot: [Shows welcome]

You: [Upload research_paper.pdf]
Bot: ✅ Document Ready! (8,456 chars)

You: Summarize the methodology and findings
Bot: [Methodology and findings summary]

You: What are the key contributions?
Bot: [Highlights contributions]

You: List all references and citations
Bot: [Lists references]

You: Identify limitations mentioned
Bot: [Lists limitations]
```

### Example 3: Business Proposal

```
You: /analyze
Bot: [Shows welcome]

You: [Upload proposal.docx]
Bot: ✅ Document Ready! (3,567 chars)

You: Create an executive summary
Bot: [Executive summary]

You: What budget is required?
Bot: [Budget analysis]

You: What are the key deliverables?
Bot: [Lists deliverables]

You: Identify potential risks
Bot: [Risk analysis]
```

---

## Tips & Best Practices

### ✅ Do's

✅ **Be specific in your instructions**
```
Good: "Identify all financial obligations and payment terms"
Bad: "What's important here?"
```

✅ **Use natural language**
```
Good: "What are the main risks in this contract?"
Bad: "risks?"
```

✅ **Ask follow-up questions**
```
First: "Summarize this document"
Then: "What are the key dates mentioned?"
Then: "Who are the stakeholders?"
```

✅ **Use custom prompts for specialized analysis**
```
For legal docs: Create a "legal_analyzer" custom prompt
For tech docs: Create a "tech_analyzer" custom prompt
Use /prompts to set it as default
```

### ❌ Don'ts

❌ **Vague instructions**
```
Bad: "Analyze this"
Bad: "Tell me about it"
```

❌ **Uploading unrelated documents**
```
Bad: Upload contract, then ask about weather
Good: Keep related questions to same document
```

❌ **Expecting perfect OCR**
```
Scanned documents may have errors
Proofread AI-generated text
```

---

## Document Memory

### How It Works

1. **Upload** - Document text is extracted and stored in memory
2. **Analyze** - Each instruction analyzes the stored text
3. **Clear** - Document is removed from memory

### Important Notes

- Document stays in memory until you clear it
- Only current user can access their document
- No document is saved permanently
- Conversation is not logged

### Session Limits

For performance:
- Maximum document size: 20 MB
- Maximum characters: Depends on LLM provider
- Session timeout: None (until manually cleared)

---

## Analysis Results

### Text Messages (Short Results)

If analysis fits in 3 messages or less:

```
Bot sends as text messages
Multiple messages if needed
Formatted with Markdown
```

### Document Files (Long Results)

If analysis is very long:

```
Bot generates .docx file
Includes:
- Analysis title
- Your instruction
- Full analysis text
Sent as downloadable file
```

---

## Custom Prompts Integration

You can use custom prompts in conversation mode:

### Using Default Custom Prompt

```
1. /prompts
2. Create or select a prompt
3. Click "Use as Default"
4. /analyze and upload document
5. Your prompt will be used for all analyses
```

### Override with System Instructions

Your text instruction overrides the system prompt:

```
Default prompt: General analyzer
Your instruction: "Analyze from legal perspective"
Result: Uses legal analysis context + your instruction
```

---

## Troubleshooting

### "Document not found"

**Problem:** You tried to analyze but no document is loaded

**Solution:**
1. Click "Upload Document"
2. Send a file
3. Wait for confirmation
4. Then send analysis instruction

### "File too large"

**Problem:** "File is too large: X MB (Maximum: 20 MB)"

**Solution:**
- Compress the file
- Upload in parts
- Use ZIP to bundle
- Remove unnecessary pages from PDF

### "No text content found"

**Problem:** "No text content found in document. Try another file."

**Solutions:**
- **PDF is image-based** - Use OCR converter first
- **Corrupted file** - Try re-downloading
- **Encrypted** - Remove encryption
- **Binary format** - Convert to PDF/DOCX first

### "Analysis timeout"

**Problem:** Bot doesn't respond after sending instruction

**Solutions:**
- Very long documents - Try summarizing first
- Complex instruction - Break into simpler requests
- LLM overload - Try again in a few minutes

### "Incorrect analysis"

**Problem:** Result doesn't match your expectation

**Solutions:**
- Be more specific: "Find financial obligations" vs "What's important?"
- Use custom prompt: `/prompts` to create specialized prompt
- Provide context: "As a lawyer, what are the risks?"
- Clarify: Send follow-up instruction with correction

---

## Performance Tips

💡 **Optimize your workflow:**

1. **Summarize first**
   ```
   First: "Create a summary"
   Then: "Based on summary, what are risks?"
   This is faster than analyzing full doc every time
   ```

2. **Use specific terminology**
   ```
   Good: "Identify force majeure clauses"
   Better: "List all force majeure clauses and quote them"
   ```

3. **Break complex analysis**
   ```
   Bad: "Analyze everything"
   Good: 
   1. "Summarize"
   2. "Identify legal risks"
   3. "List financial obligations"
   ```

4. **Keep documents focused**
   ```
   One topic = faster, better analysis
   Mixed topics = slower, less accurate
   ```

---

## Privacy & Security

🔒 Your data is:
- Processed locally (not stored)
- Only accessible by you
- Not logged or recorded
- Cleared when session ends
- Not shared with third parties

---

## FAQ

**Q: Can I analyze multiple documents?**
A: One at a time. Clear current and upload new, or use `/analyze` again.

**Q: Can I export the conversation?**
A: Yes, bot sends results as .docx file for long analyses.

**Q: Is there a conversation history?**
A: No, each session is independent. Use custom prompts to reuse settings.

**Q: Can I share my analysis with others?**
A: Yes, bot sends results as downloadable files you can share.

**Q: What happens if I close Telegram?**
A: Your document session ends. Start new with `/analyze`.

**Q: Can the bot analyze images?**
A: Yes, if image has text (PNG, JPG), bot extracts text via OCR.

**Q: Maximum document size?**
A: 20 MB. Usually enough for 100+ pages of text.

---

## Advanced Usage

### Chain Analyses

```
Analysis 1: Get summary
Analysis 2: Ask about summary
Analysis 3: Deep dive on one part
```

### Create Comparative Analysis

```
Upload Document 1, save result
Clear, Upload Document 2
Send instruction: "Compare with [saved result]"
```

### Build Reports

```
1. Upload document
2. Execute multiple analyses
3. Collect results
4. Compile into final report
5. Export as .docx
```

---

**Happy analyzing!** 🚀

*Last Updated: 2025-12-19*
