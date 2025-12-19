# Prompt Management Guide

Uh Bot allows you to create, manage, and customize AI prompts directly through Telegram!

## Overview

### What is a Prompt?

A prompt consists of two parts:

1. **System Prompt** - Instructions for the AI (e.g., "You are a legal expert")
2. **User Prompt** - The actual analysis request (e.g., "Review this contract")

### Built-in Prompts

The bot comes with 5 pre-configured prompts:

| Prompt | Purpose |
|--------|----------|
| **default** | General document analysis |
| **summarize** | Create concise summaries |
| **extract_entities** | Extract names, dates, organizations |
| **risk_analysis** | Identify risks and issues |
| **legal_review** | Legal document analysis |

## Usage

### Access Prompt Management

```
/prompts
```

You'll see the main menu:

```
🏯 Prompt Management

Manage your custom analysis prompts. Choose an option:

┌─ 📋 View Prompts
├─ ➕ Create New
└─ ⚙️ Manage
```

## Menu Options

### 1️⃣ View Prompts

See all available prompts:
- **✨** = Custom prompts (created by you)
- **📋** = Default prompts (built-in)

Click any prompt to see full details.

### 2️⃣ Create New Prompt

Create your own custom prompt:

**Step 1:** Enter prompt name
```
Example: my_analyzer, contract_review, tech_summary
```

**Step 2:** Enter system prompt
```
Example: "You are a technical specialist. 
Analyze software requirements carefully."
```

**Step 3:** Enter user prompt template
```
Example: "Analyze this technical document and identify:
1. Requirements
2. Potential issues
3. Implementation challenges"
```

### 3️⃣ Manage Prompts

Options:
- **Delete Custom Prompt** - Remove your custom prompts
- **Create New** - Quick link to create
- **Export All** - Download all prompts

## Prompt Details View

When viewing a prompt, you can:

- **✏️ Edit** - Modify system or user prompt
- **🗑️ Delete** - Remove custom prompts
- **📝 Use as Default** - Set as default for document analysis
- **« Back** - Return to list

## Examples

### Example 1: Legal Contract Review

```
Name: contract_analyzer

System Prompt:
You are an experienced corporate lawyer with 20 years 
of experience reviewing contracts. Identify risks, 
protect client interests, and ensure compliance.

User Prompt:
Review this contract and provide:
1. Summary of key obligations
2. Potential risks or red flags
3. Negotiation points
4. Compliance concerns
5. Recommendations
```

### Example 2: Technical Documentation

```
Name: tech_analyzer

System Prompt:
You are a senior software architect. Analyze technical 
documentation with focus on:
- Security implications
- Performance considerations
- Scalability
- Best practices

User Prompt:
Analyze this technical documentation and provide:
1. Architecture assessment
2. Security risks
3. Performance bottlenecks
4. Improvement suggestions
5. Compliance check
```

### Example 3: Academic Paper Review

```
Name: paper_reviewer

System Prompt:
You are a peer reviewer for academic conferences. 
Evaluate research papers for:
- Scientific rigor
- Novelty
- Clarity
- Contributions

User Prompt:
Review this academic paper and evaluate:
1. Research question clarity
2. Methodology soundness
3. Results significance
4. Writing quality
5. Contribution to field
```

## Using Custom Prompts

Once created, your custom prompts are available when analyzing documents:

1. Upload a document with `/prompts` → **Select prompt** → Use it
2. Or set as default: View Prompts → Select → "Use as Default"

## Storage

- **Default prompts** - Built into the bot (always available)
- **Custom prompts** - Saved in `data/prompts/user_{user_id}.json`
- **Auto-saved** - Changes persist across bot restarts
- **User-isolated** - Only you see your custom prompts

## Tips & Best Practices

### ✅ Do's

✅ Be specific in your system prompt
```
Good: "You are a cybersecurity expert specialized in 
cloud infrastructure security. Identify vulnerabilities."

Bad: "You are helpful."
```

✅ Use clear structure in user prompt
```
Good: 
"Analyze this document and provide:
1. Executive summary
2. Key findings
3. Recommendations"

Bad: "Tell me about this document"
```

✅ Keep prompts focused
```
Good: Separate prompts for legal, technical, financial
Bad: One prompt trying to do everything
```

### ❌ Don'ts

❌ Too generic
```
Bad: "Analyze this"
```

❌ Overly complex
```
Bad: 2000+ character prompts (keep <500 chars)
```

❌ Ambiguous instructions
```
Bad: "Maybe check if there are issues"
Good: "Identify and list all potential security issues"
```

## Command Reference

| Command | Function |
|---------|----------|
| `/prompts` | Open prompt management menu |
| `/help` | Show general help |
| `/cancel` | Exit current operation |

## Prompt Template Variables

You can use placeholders in user prompts:

```
{document_name} - Original filename
{date} - Current date
{user} - Username
```

Example:
```
Analyze {document_name} and identify key risks
```

## Troubleshooting

### "Prompt not saved"
- Check that name is 1-30 characters
- System prompt must be 10+ characters
- User prompt must be 10+ characters

### "Can't delete default prompt"
- Default prompts (built-in) cannot be deleted
- Only custom prompts can be deleted

### "My prompt disappeared"
- Custom prompts are stored in `data/prompts/`
- Check if the directory exists
- Bot restart won't delete your prompts

### "Prompt not being used"
1. Make sure it's set as default
2. Check it appears in prompt list
3. Try uploading a new document

## Advanced Usage

### Exporting Prompts

Your custom prompts are stored as JSON:

```json
{
  "contract_analyzer": {
    "name": "contract_analyzer",
    "system_prompt": "You are a lawyer...",
    "user_prompt_template": "Review this contract...",
    "description": "Legal contract review",
    "created_at": "2025-12-19T14:30:00",
    "updated_at": "2025-12-19T14:30:00"
  }
}
```

### Sharing Prompts

To share a prompt:
1. Export it
2. Share the JSON with others
3. They can import it manually

## Performance Tips

💡 **Optimize your prompts:**
- Shorter prompts = faster responses
- Specific prompts = better results
- Test with different documents

💡 **Use right prompt for document:**
- Legal doc → legal_review
- Tech doc → technical analysis
- General → summarize

## Privacy & Security

🔒 Your prompts are:
- Stored locally only
- Never sent to external services
- Only accessible by you
- Persisted securely

## FAQ

**Q: Can I edit default prompts?**
A: No, default prompts are read-only. Create a custom one instead.

**Q: How many prompts can I create?**
A: Unlimited! Create as many as needed.

**Q: Where are prompts stored?**
A: In `data/prompts/user_{your_id}.json` on the server.

**Q: Can I recover deleted prompts?**
A: No, deletion is permanent. Keep backups if important.

**Q: Can I use the same prompt for different documents?**
A: Yes! Prompts are reusable across all documents.

---

**Happy prompt creating!** 🚀

*Last Updated: 2025-12-19*
