# Uh Bot - Modes Overview

Uh Bot provides **3 main operating modes** for different use cases:

## 1️⃣ Document Upload Mode (Default)

**Purpose:** Quick single document analysis without conversation

**How it works:**
```
1. Upload document
2. Bot analyzes using default prompt
3. Get results as text or .docx file
4. Done
```

**Best for:**
- Quick analysis of single documents
- Batch processing multiple documents
- One-off analysis tasks

**Command:** `/analyze` (then upload)

**Characteristics:**
- ✅ Fast and simple
- ✅ No conversation needed
- ✅ Stateless
- ❌ Can't ask follow-up questions

---

## 2️⃣ Conversation Mode (NEW)

**Purpose:** Interactive document analysis with multiple text commands

**How it works:**
```
1. /analyze
2. Upload document ONCE
3. Bot confirms ready ✅
4. Send text instruction #1
5. Get result
6. Send text instruction #2 (same doc)
7. Get result
... repeat until done
8. /cancel or clear document
```

**Best for:**
- Deep document analysis
- Multiple perspectives on same document
- Refining analysis with follow-ups
- Research and investigation
- Legal/financial document review

**Key Features:**
- 💬 Chat-like interface
- 📄 Document stays loaded
- 🔄 Multiple analyses per document
- 🎯 Use custom prompts
- 💾 Get .docx downloads for long results

**Characteristics:**
- ✅ Interactive and flexible
- ✅ Multiple analyses per document
- ✅ Follow-up questions possible
- ✅ Efficient (document processed once)
- ❌ Needs manual instruction for each query

---

## 3️⃣ Prompt Management Mode

**Purpose:** Create and manage custom analysis prompts

**How it works:**
```
1. /prompts
2. Create new prompt or select existing
3. Customize for your needs
4. Use in document analysis
5. Set as default
```

**Best for:**
- Creating specialized analyzers
- Standardizing analysis approach
- Building reusable templates
- Domain-specific analysis (legal, technical, etc.)

**Features:**
- 🎯 5 built-in prompts (default, summarize, extract_entities, risk_analysis, legal_review)
- ➕ Create unlimited custom prompts
- ✏️ Edit existing custom prompts
- 🗑️ Delete custom prompts
- 💾 Auto-save to persistent storage
- 👤 User-isolated (only you see your prompts)

**Characteristics:**
- ✅ Highly customizable
- ✅ Reusable templates
- ✅ Persistent storage
- ✅ Easy UI with buttons
- ❌ Requires setup time

---

## Comparison Table

| Feature | Document Upload | Conversation | Prompts |
|---------|-----------------|--------------|----------|
| **Single file analysis** | ✅ | ✅ | - |
| **Multiple analyses same doc** | ❌ | ✅ | - |
| **Custom prompts** | ✅ | ✅ | ✅ |
| **Follow-up questions** | ❌ | ✅ | - |
| **Text commands** | ❌ | ✅ | - |
| **Batch processing** | ✅ | ❌ | - |
| **Setup/Config** | None | None | Optional |
| **Learning curve** | Minimal | Minimal | Low |
| **Speed** | Fast | Medium | - |
| **Flexibility** | Low | High | High |

---

## Quick Decision Tree

```
"What do I want to do?"

├─ "Analyze 1 document quickly"
│  └─ Use: Document Upload Mode
│     Command: /analyze + upload
│
├─ "Analyze 1 document multiple ways"
│  └─ Use: Conversation Mode
│     Command: /analyze + upload + multiple instructions
│
├─ "Create custom analysis prompts"
│  └─ Use: Prompt Management Mode
│     Command: /prompts
│
├─ "Deep analysis with follow-ups"
│  └─ Use: Conversation Mode
│     Command: /analyze
│
├─ "Batch analyze many documents"
│  └─ Use: Document Upload Mode
│     Command: /analyze (repeat)
│
└─ "Standardize analysis for team"
   └─ Use: Prompt Management Mode
      Command: /prompts (create custom)
```

---

## Use Case Examples

### Legal Team Review

**Goal:** Analyze contracts for risks and obligations

**Approach:**
1. `/prompts` → Create "contract_analyzer" prompt
2. `/analyze` → Upload contract.pdf
3. Bot: "Document ready!"
4. You: "Identify all financial obligations"
5. You: "What are the penalty clauses?"
6. You: "List required signatures and dates"
7. Bot: [Detailed analysis for each]

**Mode:** Conversation Mode ✅

### Academic Researcher

**Goal:** Analyze research papers for methodology, findings, references

**Approach:**
1. `/analyze` → Upload paper.pdf
2. Bot: "Document ready!"
3. You: "Summarize methodology"
4. You: "What were the key findings?"
5. You: "List all references"
6. You: "Identify limitations"
7. Export results as .docx

**Mode:** Conversation Mode ✅

### Quick Document Summaries

**Goal:** Generate summaries for 10 different reports

**Approach:**
1. Create "summarizer" custom prompt (optional)
2. `/analyze` → Upload report1.pdf
3. Get summary → Save
4. `/analyze` → Upload report2.pdf
5. Get summary → Save
6. ... repeat for all 10

**Mode:** Document Upload Mode or Conversation (both work)

### Content Analysis Pipeline

**Goal:** Analyze content for different aspects (SEO, tone, technical accuracy)

**Approach:**
1. `/prompts` → Create 3 custom prompts:
   - seo_analyzer
   - tone_analyzer
   - tech_analyzer
2. `/analyze` → Upload content.docx
3. Bot: "Document ready!"
4. You: "Analyze SEO"
5. You: "Analyze tone and style"
6. You: "Check technical accuracy"
7. Combine results

**Mode:** Conversation Mode ✅

---

## Workflow Examples

### Daily Legal Review

```
Monday:
1. /analyze
2. Upload daily_contracts.pdf
3. "Summarize all contracts"
4. "Identify top 5 risks"
5. "List action items"
6. Export report
```

### Research Phase

```
1. /analyze
2. Upload research_paper_1.pdf
3. "Key findings and methodology"
4. "Notable limitations"
5. Clear document
6. /analyze
7. Upload research_paper_2.pdf
8. Repeat for comparison
```

### Custom Analysis Pipeline

```
1. /prompts → Create custom prompt
2. /analyze
3. Upload document
4. Multiple analysis commands
5. Export results
6. Use custom prompt again for next doc
```

---

## Performance Characteristics

### Document Upload Mode
- **Speed:** ⚡ Very Fast
- **Latency:** Low (5-20 seconds)
- **Cost:** Standard
- **Best for:** Quick analysis

### Conversation Mode
- **Speed:** ⚡⚡ Fast (document processed once)
- **Latency:** Medium (10-30 seconds per query)
- **Cost:** Efficient (reuses document extraction)
- **Best for:** Deep analysis

### Prompt Management
- **Speed:** ⚡ Instant
- **Setup:** 2-5 minutes per prompt
- **Storage:** Local (no API calls)
- **ROI:** High if used repeatedly

---

## Getting Started

### First Time Users

1. **Try Conversation Mode:**
   ```
   /analyze
   [Upload any document]
   "Summarize this"
   "What are key points?"
   ```

2. **Then Explore Prompts:**
   ```
   /prompts
   Select "legal_review" or "summarize"
   View details
   ```

3. **Advanced: Create Custom:**
   ```
   /prompts → Create New
   Name it something meaningful
   Add system prompt (AI instructions)
   Add user prompt (analysis request template)
   Use in /analyze
   ```

### Pro Tips

💡 **Save time:**
- Use custom prompts for repeated analysis
- Upload ZIP with multiple files
- Use /prompts to standardize approach

💡 **Better results:**
- Be specific in text instructions
- Use follow-up questions
- Create specialized prompts for domains

💡 **Organize effectively:**
- Name custom prompts clearly
- Document what each prompt does
- Update prompts based on results

---

## Detailed Documentation

- **Conversation Mode:** See [CONVERSATION_MODE.md](./CONVERSATION_MODE.md)
- **Prompt Management:** See [PROMPT_MANAGEMENT.md](./PROMPT_MANAGEMENT.md)
- **Replicate Integration:** See [REPLICATE_INTEGRATION.md](./REPLICATE_INTEGRATION.md)
- **File Processing:** See [FILE_PROCESSING.md](./FILE_PROCESSING.md)

---

## Command Summary

| Command | Mode | Purpose |
|---------|------|----------|
| `/analyze` | Conversation | Start interactive mode |
| `/prompts` | Prompt Mgmt | Manage custom prompts |
| `/help` | All | Show help |
| `/start` | All | Show welcome |
| `/cancel` | All | Exit current mode |

---

## FAQ

**Q: Which mode should I use?**
A: Start with Conversation Mode - it's the most flexible.

**Q: Can I use custom prompts in both modes?**
A: Yes, custom prompts work in both Document Upload and Conversation modes.

**Q: How many documents can I analyze?**
A: Unlimited, but one at a time in Conversation Mode.

**Q: Will my documents be saved?**
A: No, documents are processed and cleared. Only prompts are saved.

**Q: Can I export results?**
A: Yes, long results are auto-exported as .docx files.

**Q: Is there a file size limit?**
A: Yes, 20 MB maximum per file.

---

**Choose your mode and start analyzing!** 🚀

*Last Updated: 2025-12-19*
