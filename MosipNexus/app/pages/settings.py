"""
MOSIP Nexus — Settings Page
"""

from __future__ import annotations

import sys
from pathlib import Path
from config.settings import GROQ_API_KEY

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Settings — MOSIP Nexus",
    page_icon="⚙️",
    layout="centered",
)

# ── Styles ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Hide Streamlit's auto-generated multi-page nav links */
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebarContent"] { padding-top: 1rem !important; }
[data-testid="stSidebarContent"] hr { margin: 1rem 0 !important; border-color: #e5e7eb !important; }

/* Section label above containers */
.nx-section-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: #9ca3af;
    margin-bottom: 0.6rem;
}
.nx-section-title {
    font-size: 1rem;
    font-weight: 600;
    color: #111827;
    margin-bottom: 0.25rem;
}
.nx-section-desc {
    font-size: 0.83rem;
    color: #6b7280;
    margin-bottom: 0.8rem;
    line-height: 1.5;
}

/* Status badge */
.nx-status-ok {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    background: #f0fdf4;
    border: 1px solid #86efac;
    border-radius: 20px;
    padding: 0.35rem 0.9rem;
    font-size: 0.82rem;
    font-weight: 600;
    color: #15803d;
}
.nx-status-warn {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    background: #fffbeb;
    border: 1px solid #fcd34d;
    border-radius: 20px;
    padding: 0.35rem 0.9rem;
    font-size: 0.82rem;
    font-weight: 600;
    color: #b45309;
}

/* Provider radio cards */
div[data-testid="stRadio"] > div {
    gap: 0.55rem !important;
    flex-wrap: wrap;
}
div[data-testid="stRadio"] label {
    background: #f9fafb !important;
    border: 1.5px solid #e5e7eb !important;
    border-radius: 9px !important;
    padding: 0.55rem 1.1rem !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    color: #374151 !important;
    cursor: pointer;
    transition: all 0.15s ease;
    min-width: 110px;
    justify-content: center;
}
div[data-testid="stRadio"] label:hover {
    border-color: #6366f1 !important;
    background: #f5f3ff !important;
    color: #4338ca !important;
}

/* Privacy pill */
.nx-privacy {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 6px;
    padding: 0.35rem 0.7rem;
    font-size: 0.77rem;
    color: #0369a1;
    margin-top: 0.4rem;
}

/* MCP card inside container */
.nx-mcp-card {
    background: linear-gradient(135deg, #faf5ff 0%, #ede9fe 100%);
    border: 1px solid #c4b5fd;
    border-radius: 10px;
    padding: 1rem 1.2rem 0.9rem;
    margin-bottom: 0.75rem;
}
.nx-mcp-card-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: #4c1d95;
    margin-bottom: 0.25rem;
}
.nx-mcp-card-desc {
    font-size: 0.81rem;
    color: #6d28d9;
    line-height: 1.45;
}
.nx-badge {
    display: inline-block;
    background: #7c3aed;
    color: white;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    margin-left: 0.4rem;
    vertical-align: middle;
}

/* Key link */
.nx-key-link {
    font-size: 0.78rem;
    color: #6366f1;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.page_link("app.py", label="← Back to Chat", icon="💬")
    st.divider()
    st.caption("MOSIP Nexus")

# ── Page header ──────────────────────────────────────────────────────────────────
st.markdown("## ⚙️ Settings")
st.markdown(
    '<p style="color:#6b7280; font-size:0.875rem; margin-top:-0.5rem; margin-bottom:1.4rem;">'
    'Configure your LLM provider. Changes apply immediately to your session only.'
    '</p>',
    unsafe_allow_html=True,
)

# ── Persistent session state defaults (survive page navigation) ───────────────
if "llm_api_key" not in st.session_state:
    st.session_state["llm_api_key"] = GROQ_API_KEY or ""
if "llm_provider" not in st.session_state:
    st.session_state["llm_provider"] = "groq"

# ── Status badge placeholder — filled after widgets run ───────────────────────
_status_placeholder = st.empty()
st.markdown("<br>", unsafe_allow_html=True)

# ── LLM Configuration ────────────────────────────────────────────────────────────
st.markdown('<div class="nx-section-label">LLM Configuration</div>', unsafe_allow_html=True)

with st.container(border=True):
    st.markdown(
        '<div class="nx-section-title">🤖 Choose your AI provider</div>'
        '<div class="nx-section-desc">Select a provider and enter your own API key. '
        'Your key stays in your browser session and is never stored on the server.</div>',
        unsafe_allow_html=True,
    )

    _PROVIDER_MAP = {
        "Groq": "groq",
        "Claude — Anthropic": "anthropic",
        "OpenAI": "openai",
    }
    _PROVIDER_REVERSE = {v: k for k, v in _PROVIDER_MAP.items()}

    current_provider_key = st.session_state.get("llm_provider", "groq")
    current_label = _PROVIDER_REVERSE.get(current_provider_key, "Groq")

    selected_label = st.radio(
        "Provider",
        options=list(_PROVIDER_MAP.keys()),
        index=list(_PROVIDER_MAP.keys()).index(current_label),
        horizontal=True,
        label_visibility="collapsed",
    )

    selected_provider = _PROVIDER_MAP[selected_label]
    st.session_state["llm_provider"] = selected_provider

    st.markdown("<br style='line-height:0.5rem'>", unsafe_allow_html=True)

    # Provider-specific config
    if selected_provider == "groq":
        key_placeholder, key_link = "gsk_...", "https://console.groq.com"
        key_link_label = "Get a free key at console.groq.com →"
        model_options = [
            "llama-3.3-70b-versatile (recommended)",
            "llama-3.1-8b-instant (faster)",
            "mixtral-8x7b-32768",
        ]
        model_values = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
    elif selected_provider == "anthropic":
        key_placeholder, key_link = "sk-ant-...", "https://console.anthropic.com"
        key_link_label = "Get your key at console.anthropic.com →"
        model_options = [
            "claude-haiku-4-5-20251001 (fastest, recommended)",
            "claude-sonnet-4-6 (balanced)",
            "claude-opus-4-8 (most capable)",
        ]
        model_values = ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-8"]
    else:
        key_placeholder, key_link = "sk-...", "https://platform.openai.com/api-keys"
        key_link_label = "Get your key at platform.openai.com →"
        model_options = [
            "gpt-4o-mini (fastest, recommended)",
            "gpt-4o (balanced)",
            "gpt-4-turbo (most capable)",
        ]
        model_values = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"]

    col_key, col_model = st.columns([3, 2])

    with col_key:
        st.markdown(
            f'<a class="nx-key-link" href="{key_link}" target="_blank">{key_link_label}</a>',
            unsafe_allow_html=True,
        )
        # Seed the widget key from the persistent key when returning to this page
        st.text_input(
            "API Key",
            value=GROQ_API_KEY or "",
            type="password",
            disabled=True,  
            label_visibility="collapsed",
            help="API key is loaded from the .env file."
        )

        api_key = GROQ_API_KEY

    with col_model:
        st.caption("Model")
        current_model = st.session_state.get("llm_model", model_values[0])
        model_index = model_values.index(current_model) if current_model in model_values else 0
        selected_model_label = st.selectbox(
            "Model",
            options=model_options,
            index=model_index,
            label_visibility="collapsed",
        )
        st.session_state["llm_model"] = model_values[model_options.index(selected_model_label)]

    if api_key:
        st.success("API key saved for this session. You can now start chatting.", icon="✅")
    else:
        st.caption("Enter your API key above to activate this provider.")

    # ── Fill status badge now that we have the real values ────────────────────
    _provider_display = {
        "groq": "Groq",
        "anthropic": "Claude (Anthropic)",
        "openai": "OpenAI",
    }.get(selected_provider, "Groq")

    if api_key:
        _status_placeholder.markdown(
            f'<span class="nx-status-ok">✓ &nbsp;Active — {_provider_display}</span>',
            unsafe_allow_html=True,
        )
    else:
        _status_placeholder.markdown(
            '<span class="nx-status-warn">⚠ &nbsp;No LLM configured</span>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="nx-privacy">🔒 &nbsp;Key is session-only — never logged, stored, or shared.</div>',
        unsafe_allow_html=True,
    )

# ── Claude Desktop / MCP ─────────────────────────────────────────────────────────
st.markdown("<br style='line-height:0.2rem'>", unsafe_allow_html=True)
st.markdown('<div class="nx-section-label">Alternative Access</div>', unsafe_allow_html=True)

with st.container(border=True):
    st.markdown(
        '<div class="nx-mcp-card">'
        '<div class="nx-mcp-card-title">🖥️ Claude Desktop (MCP Integration)'
        '<span class="nx-badge">No API key needed</span></div>'
        '<div class="nx-mcp-card-desc">'
        'Connect Claude Desktop directly to MOSIP Nexus. Claude uses your own subscription '
        'for the AI — MosipNexus only handles knowledge retrieval.'
        '</div></div>',
        unsafe_allow_html=True,
    )

    with st.expander("Setup guide — Claude Desktop"):
        st.markdown("""
**Step 1** — Open Claude Desktop → Settings → Developer → Edit Config

**Step 2** — Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mosip-nexus": {
      "command": "uv",
      "args": [
        "--directory", "D:\\\\path\\\\to\\\\MosipNexus",
        "run", "python", "mcp_server/server.py"
      ],
      "env": {
        "PYTHONPATH": "D:\\\\path\\\\to\\\\MosipNexus",
        "PG_CONNECTION": "postgresql+psycopg://mosip:mosip@localhost:5432/mosipnexus"
      }
    }
  }
}
```
*(Replace the path and PG_CONNECTION with your actual values.)*

**Step 3** — Restart Claude Desktop → verify "mosip-nexus" appears under Developer → MCP Servers.

**Step 4** — Ask Claude any MOSIP question. It calls `search_mosip` automatically and answers using your Claude subscription.
""")

# ── Preferences ──────────────────────────────────────────────────────────────────
st.markdown("<br style='line-height:0.2rem'>", unsafe_allow_html=True)
st.markdown('<div class="nx-section-label">Preferences</div>', unsafe_allow_html=True)

with st.container(border=True):
    st.markdown(
        '<div style="font-size:0.875rem; font-weight:500; color:#374151; margin-bottom:0.1rem;">'
        'Max chat history turns</div>'
        '<div style="font-size:0.78rem; color:#9ca3af; margin-bottom:0.5rem;">'
        'Older turns are dropped to keep token usage low.</div>',
        unsafe_allow_html=True,
    )
    max_turns = st.slider(
        "Max chat history turns",
        min_value=5, max_value=30,
        value=st.session_state.get("max_history_turns", 10),
        step=5,
        label_visibility="collapsed",
    )
    st.session_state["max_history_turns"] = max_turns

# ── About ─────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="text-align:center; padding: 1.4rem 0 0.5rem; font-size:0.78rem; color:#9ca3af; line-height:1.8;">'
    '<strong style="color:#6b7280;">MOSIP Nexus</strong> v1.0 &nbsp;·&nbsp; '
    'LangChain &nbsp;·&nbsp; pgvector &nbsp;·&nbsp; HuggingFace<br>'
    '449 docs &nbsp;·&nbsp; 849 community threads &nbsp;·&nbsp; 797 GitHub issues &nbsp;·&nbsp; '
    '1,738 Confluence pages &nbsp;·&nbsp; 6,566 source files'
    '</div>',
    unsafe_allow_html=True,
)
