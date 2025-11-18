# API Key Configuration Guide

This guide explains how to securely configure API keys for LLM integrations in UltimateSkillOS.

## 🔐 Security First

**NEVER commit API keys to git!** All files containing API keys are already listed in `.gitignore`:
- `.env`
- `*.env`
- `config.yml` (if you add keys there)

## 📝 Step-by-Step Setup

### 1. Create Your `.env` File

Copy the example file to create your private `.env` file:

```bash
cp .env.example .env
```

### 2. Add Your API Keys

Open `.env` in your editor and add your actual API keys:

```bash
# .env file (NEVER commit this!)

# OpenAI API Key (for GPT-4, GPT-3.5-turbo)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# OR Anthropic Claude API Key
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# OR Google Gemini API Key
GOOGLE_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Choose your provider
LLM_PROVIDER=openai

# Choose your model
LLM_MODEL=gpt-4
```

### 3. Where to Get API Keys

#### OpenAI (GPT-4, GPT-3.5-turbo)
1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key (starts with `sk-proj-...`)
5. Paste it in your `.env` file as `OPENAI_API_KEY=sk-proj-...`

#### Anthropic (Claude)
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy and paste it in your `.env` file as `ANTHROPIC_API_KEY=...`

#### Google (Gemini)
1. Go to https://makersuite.google.com/app/apikey
2. Sign up or log in with your Google account
3. Create an API key
4. Copy and paste it in your `.env` file as `GOOGLE_API_KEY=...`

#### Local LLMs (Ollama, LM Studio)
If running a local LLM:
```bash
LLM_PROVIDER=local
LOCAL_LLM_ENDPOINT=http://localhost:11434
LLM_MODEL=llama2
```

### 4. Install Required Packages

```bash
pip install python-dotenv openai anthropic
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### 5. Verify Setup

The API keys will be automatically loaded when you start the server:

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8002 --reload
```

## 🔍 How It Works

1. **Environment Variables**: API keys are stored in `.env` file
2. **Auto-Loading**: `python-dotenv` loads `.env` on startup
3. **Skill Access**: Skills read keys via `os.getenv("OPENAI_API_KEY")`
4. **Git Safety**: `.env` is in `.gitignore` so it won't be committed

## 📁 File Structure

```
UltimateSkillOS/
├── .env                    # ← PUT YOUR API KEYS HERE (not committed)
├── .env.example            # ← Template (safe to commit)
├── .gitignore              # ← Contains .env (prevents commits)
├── skills/
│   └── qa_skill.py         # ← Uses os.getenv() to read keys
└── api/
    └── app.py              # ← Loads .env with load_dotenv()
```

## ✅ Security Checklist

- [x] `.env` is listed in `.gitignore`
- [x] Never hardcode API keys in Python files
- [x] Use `os.getenv()` to read environment variables
- [x] Keep `.env.example` with placeholder values
- [x] Never share your `.env` file
- [x] Rotate keys if accidentally exposed

## 🚀 Using the QA Skill

Once configured, the `QASkill` will automatically:
1. Read your API key from environment variables
2. Initialize the appropriate LLM client (OpenAI, Anthropic, etc.)
3. Answer questions using the LLM

Test it through the web UI or API:

```bash
curl -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is machine learning?"}'
```

## 🔧 Troubleshooting

**Error: "OPENAI_API_KEY not found in environment variables"**
- Make sure you created `.env` file (not `.env.example`)
- Check that the key is on its own line: `OPENAI_API_KEY=sk-...`
- Restart the server after creating `.env`

**Error: "Invalid API key"**
- Verify the key is correct (check for extra spaces)
- Make sure the key hasn't expired
- Check your API provider dashboard for status

**Skill not being called**
- Check that `qa_skill.py` is in the `skills/` directory
- Verify the skill is auto-discovered (check server logs)
- Ensure the router is configured to use the skill

## 🌐 Environment Variables Reference

| Variable | Purpose | Example |
|----------|---------|---------|
| `OPENAI_API_KEY` | OpenAI API authentication | `sk-proj-...` |
| `ANTHROPIC_API_KEY` | Anthropic API authentication | `sk-ant-...` |
| `GOOGLE_API_KEY` | Google API authentication | `AIza...` |
| `LLM_PROVIDER` | Which LLM to use | `openai`, `anthropic`, `local` |
| `LLM_MODEL` | Model name | `gpt-4`, `claude-3-sonnet`, `llama2` |
| `LOCAL_LLM_ENDPOINT` | Local LLM URL | `http://localhost:11434` |

## 📚 Next Steps

- Set up your `.env` file with API keys
- Test the QA skill through the web UI
- Configure routing to use the QA skill
- Add more LLM-powered skills

For more information, see the main [README.md](../README.md).
