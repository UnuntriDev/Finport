"""Shared Streamlit CSS for FinPort."""
from __future__ import annotations

GLOBAL_CSS = """
    <style>
        /* Global dark base */
        .stApp { background-color: #020617; }
        .main > div { padding-top: 0.5rem; }

        /* Remove default Streamlit padding on metric */
        div[data-testid="metric-container"] { display: none; }

        /* Tabs — pill-style buttons with gradient active state */
        [data-baseweb="tab-list"] {
            background: transparent !important;
            gap: 8px !important;
            border-bottom: none !important;
            padding: 4px 0 12px 0 !important;
            margin-bottom: 18px !important;
            flex-wrap: wrap !important;
        }
        [data-baseweb="tab-list"] button[data-baseweb="tab"],
        [data-baseweb="tab-list"] [role="tab"] {
            background: #0f172a !important;
            border: 1px solid #1e293b !important;
            border-radius: 10px !important;
            color: #94a3b8 !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            padding: 8px 18px !important;
            min-height: 38px !important;
            height: auto !important;
            transition: all 0.18s ease !important;
            white-space: nowrap !important;
        }
        [data-baseweb="tab-list"] button[data-baseweb="tab"]:hover,
        [data-baseweb="tab-list"] [role="tab"]:hover {
            background: #1e293b !important;
            color: #93c5fd !important;
            border-color: #334155 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
        }
        [data-baseweb="tab-list"] button[data-baseweb="tab"][aria-selected="true"],
        [data-baseweb="tab-list"] [role="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%) !important;
            color: #ffffff !important;
            border-color: #3b82f6 !important;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
            transform: translateY(-1px) !important;
        }
        /* Hide Streamlit's default underline highlight and divider */
        [data-baseweb="tab-highlight"],
        [data-baseweb="tab-border"] {
            display: none !important;
            background: transparent !important;
        }
        /* Tab panel padding */
        [data-baseweb="tab-panel"] {
            padding-top: 8px !important;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: #0a0f1e;
            border-right: 1px solid #1e293b;
        }

        /* Buttons */
        div[data-testid="stButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #1d4ed8, #2563eb);
            border: none;
            font-weight: 600;
            letter-spacing: 0.02em;
        }

        /* Download buttons */
        div[data-testid="stDownloadButton"] > button {
            background: #0f172a;
            border: 1px solid #1e3a5f;
            color: #60a5fa;
            font-weight: 600;
        }
        div[data-testid="stDownloadButton"] > button:hover {
            background: #1e3a5f;
            border-color: #3b82f6;
        }

        /* Dataframes */
        div[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

        /* Dividers */
        hr { border-color: #1e293b; }

        h2, h3 { color: #e2e8f0 !important; letter-spacing: -0.02em; }

        /* Sidebar: compact small buttons for chips & date presets */
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
            padding: 4px 10px !important;
            font-size: 11px !important;
            font-weight: 600 !important;
            min-height: 28px !important;
            line-height: 1.2 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"] {
            background: #0f172a !important;
            border: 1px solid #1e3a5f !important;
            color: #93c5fd !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"]:hover {
            background: #1e3a5f !important;
            border-color: #3b82f6 !important;
            color: #ffffff !important;
        }
        /* Compact number inputs in sidebar */
        section[data-testid="stSidebar"] div[data-testid="stNumberInput"] input {
            padding: 4px 8px !important;
            font-size: 13px !important;
        }
        /* Run analysis button — prominent glow */
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
            border: none !important;
            font-size: 14px !important;
            font-weight: 800 !important;
            letter-spacing: 0.04em !important;
            min-height: 46px !important;
            border-radius: 10px !important;
            box-shadow: 0 0 18px rgba(37,99,235,0.55), 0 4px 16px rgba(0,0,0,0.4) !important;
            transition: all 0.18s ease !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]:hover {
            box-shadow: 0 0 30px rgba(59,130,246,0.75), 0 6px 20px rgba(0,0,0,0.5) !important;
            transform: translateY(-1px) !important;
        }
    </style>
"""
