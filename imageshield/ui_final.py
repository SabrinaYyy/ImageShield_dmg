"""
Design User Interface (Web-based)
1. The model (baseline of either EditShield or PhotoGuard) has input of an image, and an output of a protected version of the image.
2. The web-based interface should be made user friendly, such that anyone is able to use it easily (it should not involve
any code running inside the terminal)
"""

import os
import time
import uuid
from pathlib import Path

import gradio as gr
from PIL import Image, ImageOps

from .resources import user_data_dir

SERVICE = None
OUTPUT_DIR = user_data_dir() / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MAX_OUTPUT_AGE_SECONDS = 24 * 60 * 60

BG_IMAGE_PATH = Path(__file__).with_name("shield_bg.png")


def get_service():
    """Create the protection service only when the user needs it."""
    global SERVICE
    if SERVICE is None:
        from .protection import ProtectionService

        SERVICE = ProtectionService()
    return SERVICE


def _build_css() -> str:
    """
    Three-layer styling strategy:
      1. CSS variables  — Gradio's theme system reads these; overrides the theme.
      2. CSS selectors  — Fallback for elements not theme-controlled.
      3. JS (ALL_JS)    — Runtime DOM manipulation; bypasses all CSS specificity.
    """
    if BG_IMAGE_PATH.exists():
        body_bg = (
            f"background-image: url('/file={BG_IMAGE_PATH.as_posix()}') !important;"
            " background-size: cover !important;"
            " background-position: center center !important;"
            " background-attachment: fixed !important;"
            " background-repeat: no-repeat !important;"
        )
    else:
        body_bg = (
            "background: radial-gradient(ellipse at 50% 50%, #09112b 0%, #050b1d 40%, #020617 100%) !important;"
            " background-attachment: fixed !important;"
        )
    return f"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ═══════════════════════════════════════════════════
   LAYER 1 — Gradio CSS variable overrides
   These are consumed by Gradio's theme system and
   reliably control blocks, buttons, labels, inputs.
   ═══════════════════════════════════════════════════ */
:root {{
    /* Body */
    --body-background-fill: #060E1C;
    --body-text-color: #F0F4FF;
    --body-text-color-subdued: #8FA8C8;
    --body-text-size: 0.9rem;
    --font: 'Inter', system-ui, sans-serif;
    --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

    /* Panels / blocks */
    --block-background-fill: rgba(6,14,28,0.88);
    --block-border-color: rgba(56,232,255,0.30);
    --block-border-width: 1px;
    --block-radius: 14px;
    --block-shadow: 0 0 16px rgba(56,232,255,0.10), 0 0 32px rgba(124,58,237,0.06), 0 6px 28px rgba(0,0,0,0.55);
    --block-padding: 16px;
    --block-title-background-fill: transparent;
    --block-title-border-color: transparent;
    --block-title-text-color: #F0F4FF;

    /* Label pills */
    --block-label-background-fill: rgba(56,232,255,0.07);
    --block-label-border-color: rgba(56,232,255,0.42);
    --block-label-border-width: 1px;
    --block-label-radius: 20px;
    --block-label-padding: 3px 12px;
    --block-label-text-color: #38E8FF;
    --block-label-text-size: 0.72rem;
    --block-label-text-weight: 700;
    --block-label-margin: 0;

    /* Primary button (Protect Image) */
    --button-primary-background-fill: linear-gradient(135deg,#00D9FF 0%,#38E8FF 45%,#7C3AED 100%);
    --button-primary-background-fill-hover: linear-gradient(135deg,#18E6FF 0%,#50F0FF 45%,#9B6AF6 100%);
    --button-primary-text-color: #040E1C;
    --button-primary-border-color: transparent;
    --button-primary-border-color-hover: transparent;
    --button-primary-shadow: 0 0 22px rgba(56,232,255,0.38), 0 4px 16px rgba(0,0,0,0.40);
    --button-primary-shadow-hover: 0 0 38px rgba(56,232,255,0.60), 0 8px 28px rgba(0,0,0,0.50);

    /* Stop / cancel button */
    --button-cancel-background-fill: linear-gradient(135deg,#FF8C42 0%,#FF5E5B 100%);
    --button-cancel-background-fill-hover: linear-gradient(135deg,#FFAA60 0%,#FF7070 100%);
    --button-cancel-text-color: #ffffff;
    --button-cancel-border-color: transparent;
    --button-cancel-shadow: 0 0 18px rgba(255,94,91,0.28), 0 4px 16px rgba(0,0,0,0.40);

    /* Secondary / download button */
    --button-secondary-background-fill: linear-gradient(135deg,rgba(56,232,255,0.10),rgba(124,58,237,0.10));
    --button-secondary-background-fill-hover: linear-gradient(135deg,rgba(56,232,255,0.22),rgba(124,58,237,0.22));
    --button-secondary-text-color: #38E8FF;
    --button-secondary-border-color: rgba(56,232,255,0.38);
    --button-secondary-border-color-hover: rgba(56,232,255,0.62);

    /* Button dimensions */
    --button-large-radius: 10px;
    --button-large-text-size: 1rem;
    --button-large-text-weight: 700;
    --button-large-padding: 14px 22px;
    --button-small-radius: 8px;

    /* Inputs */
    --input-background-fill: rgba(3,8,18,0.72);
    --input-border-color: rgba(56,232,255,0.25);
    --input-border-color-focus: rgba(56,232,255,0.65);
    --input-border-width: 1px;
    --input-radius: 9px;
    --input-text-size: 0.9rem;
    --input-text-color: #F0F4FF;
    --input-placeholder-color: #506070;
    --input-shadow-focus: 0 0 10px rgba(56,232,255,0.18);

    /* Slider */
    --slider-color: #38E8FF;
    --color-accent: #38E8FF;
    --color-accent-soft: rgba(56,232,255,0.15);

    /* Misc */
    --section-header-text-color: #38E8FF;
    --section-header-text-size: 0.82rem;
    --section-header-text-weight: 700;
    --table-radius: 10px;
    --checkbox-background-color: rgba(3,8,18,0.65);
    --checkbox-border-color: rgba(56,232,255,0.30);
    --checkbox-background-color-selected: #7C3AED;
    --checkbox-border-color-selected: #7C3AED;
}}

/* ═══════════════════════════════════════════════════
   LAYER 2 — CSS selector overrides (fallback)
   ═══════════════════════════════════════════════════ */

/* Background */
body {{
    {body_bg}
    min-height: 100vh !important;
    font-family: 'Inter', system-ui, sans-serif !important;
}}

body::before {{
    content: '' !important;
    position: fixed !important;
    inset: 0 !important;
    background:
        radial-gradient(ellipse 55% 45% at 82% 88%, rgba(56,232,255,0.07) 0%, transparent 60%),
        radial-gradient(ellipse 45% 40% at 18% 12%, rgba(124,58,237,0.08) 0%, transparent 60%) !important;
    pointer-events: none !important;
    z-index: 0 !important;
}}

body::after {{
    content: '' !important;
    position: fixed !important;
    inset: 0 !important;
    background-image:
        linear-gradient(rgba(56,232,255,0.017) 1px, transparent 1px),
        linear-gradient(90deg, rgba(56,232,255,0.017) 1px, transparent 1px) !important;
    background-size: 50px 50px !important;
    pointer-events: none !important;
    z-index: 0 !important;
}}

.gradio-container {{
    background: transparent !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    max-width: 1350px !important;
    padding: 16px 22px 28px !important;
    position: relative !important;
    z-index: 1 !important;
}}

/* Panels */
.block, .form {{
    background: rgba(6,14,28,0.88) !important;
    border: 1px solid rgba(56,232,255,0.30) !important;
    border-radius: 14px !important;
    box-shadow:
        0 0 16px rgba(56,232,255,0.10),
        0 0 32px rgba(124,58,237,0.06),
        0 6px 28px rgba(0,0,0,0.55) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    transition: border-color 0.28s, box-shadow 0.28s !important;
    animation: fadeInUp 0.38s ease both !important;
}}

.block:hover, .form:hover {{
    border-color: rgba(56,232,255,0.50) !important;
    box-shadow:
        0 0 24px rgba(56,232,255,0.18),
        0 0 48px rgba(124,58,237,0.10),
        0 8px 36px rgba(0,0,0,0.62) !important;
}}

/* Hero header — transparent (JS also handles this) */
#hero-header, #hero-header > .block,
div#hero-header {{ background: transparent !important; border: none !important; box-shadow: none !important; backdrop-filter: none !important; -webkit-backdrop-filter: none !important; animation: none !important; }}

/* Typography */
.prose, .prose p, .prose li {{ color: #8FA8C8 !important; }}
.prose h1, .prose h2, .prose h3 {{ color: #F0F4FF !important; font-weight: 700 !important; }}
p, li, span {{ font-family: 'Inter', system-ui, sans-serif !important; }}
strong {{ color: #F0F4FF !important; }}
hr {{ border-color: rgba(56,232,255,0.16) !important; }}

/* Label pill — fallback (JS is the primary method) */
.block .label-wrap, .form .label-wrap,
.block-label, .block > div > .label-wrap {{
    display: inline-flex !important;
    align-items: center !important;
    background: rgba(56,232,255,0.07) !important;
    border: 1px solid rgba(56,232,255,0.42) !important;
    border-radius: 20px !important;
    padding: 3px 12px !important;
    margin-bottom: 10px !important;
    width: auto !important;
    max-width: max-content !important;
    min-width: unset !important;
}}

.block .label-wrap span, .block .label-wrap label span,
.block-label span {{
    color: #38E8FF !important;
    -webkit-text-fill-color: #38E8FF !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.09em !important;
    text-transform: uppercase !important;
}}

/* Inputs */
input[type=text], input[type=number], input[type=email], textarea, select {{
    background: rgba(3,8,18,0.72) !important;
    border: 1px solid rgba(56,232,255,0.25) !important;
    border-radius: 9px !important;
    color: #F0F4FF !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    transition: border-color 0.25s, box-shadow 0.25s !important;
}}

input[type=text]:focus, input[type=number]:focus, textarea:focus {{
    border-color: rgba(56,232,255,0.65) !important;
    box-shadow: 0 0 10px rgba(56,232,255,0.20) !important;
    outline: none !important;
}}

.info, .description {{ color: #5E7890 !important; font-size: 0.78rem !important; }}

/* Image containers */
[data-testid="image"], .image-container {{
    background: rgba(3,8,18,0.65) !important;
    border: 1px solid rgba(56,232,255,0.28) !important;
    border-radius: 12px !important;
    transition: border-color 0.28s, box-shadow 0.28s !important;
}}

[data-testid="image"]:hover, .image-container:hover {{
    border-color: rgba(56,232,255,0.52) !important;
    box-shadow: 0 0 20px rgba(56,232,255,0.12) !important;
}}

/* Protect Image button */
button.primary, .primary button,
#protect_btn button, #protect_btn .lg {{
    background: linear-gradient(135deg,#00D9FF 0%,#38E8FF 45%,#7C3AED 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #040E1C !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    letter-spacing: 0.05em !important;
    min-height: 52px !important;
    box-shadow: 0 0 22px rgba(56,232,255,0.38), 0 4px 16px rgba(0,0,0,0.42) !important;
    transition: transform 0.22s ease, box-shadow 0.22s ease, filter 0.22s ease !important;
}}

button.primary:hover, #protect_btn button:hover, #protect_btn .lg:hover {{
    transform: translateY(-2px) scale(1.02) !important;
    box-shadow: 0 0 38px rgba(56,232,255,0.60), 0 8px 28px rgba(0,0,0,0.52) !important;
    filter: brightness(1.08) !important;
}}

button.primary:active {{ transform: scale(0.98) !important; }}

/* Stop button */
button.stop, button.cancel, .stop button, .cancel button,
#stop_btn button, #stop_btn .lg {{
    background: linear-gradient(135deg,#FF8C42 0%,#FF5E5B 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #fff !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    letter-spacing: 0.05em !important;
    min-height: 52px !important;
    box-shadow: 0 0 18px rgba(255,94,91,0.28), 0 4px 16px rgba(0,0,0,0.42) !important;
    transition: transform 0.22s ease, box-shadow 0.22s ease !important;
}}

button.stop:hover, #stop_btn button:hover, #stop_btn .lg:hover {{
    transform: translateY(-2px) scale(1.02) !important;
    box-shadow: 0 0 34px rgba(255,94,91,0.52), 0 8px 28px rgba(0,0,0,0.52) !important;
}}

/* Download button */
button.secondary, .secondary button,
#download_section a, #download_section button,
.download_section a, .download_section button {{
    background: linear-gradient(135deg,rgba(56,232,255,0.10),rgba(124,58,237,0.10)) !important;
    border: 1px solid rgba(56,232,255,0.38) !important;
    border-radius: 10px !important;
    color: #38E8FF !important;
    font-weight: 600 !important;
    min-height: 50px !important;
    transition: background 0.28s, box-shadow 0.28s, transform 0.2s !important;
}}

#download_section a:hover, #download_section button:hover {{
    background: linear-gradient(135deg,rgba(56,232,255,0.20),rgba(124,58,237,0.20)) !important;
    box-shadow: 0 0 22px rgba(56,232,255,0.24) !important;
    transform: translateY(-1px) !important;
}}

/* Radio */
input[type=radio] {{ accent-color: #7C3AED !important; }}

.gradio-radio .wrap, fieldset .wrap {{
    background: rgba(3,8,18,0.62) !important;
    border: 1px solid rgba(56,232,255,0.20) !important;
    border-radius: 8px !important;
    padding: 7px 14px !important;
    transition: all 0.22s !important;
    cursor: pointer !important;
    margin: 2px 4px 2px 0 !important;
}}

.gradio-radio .wrap:has(input:checked) {{
    background: rgba(124,58,237,0.22) !important;
    border-color: rgba(124,58,237,0.68) !important;
    box-shadow: 0 0 12px rgba(124,58,237,0.30) !important;
}}

.gradio-radio .wrap:has(input:checked) span {{
    color: #F0F4FF !important;
    -webkit-text-fill-color: #F0F4FF !important;
}}

/* Slider */
input[type=range] {{
    -webkit-appearance: none !important;
    appearance: none !important;
    background: linear-gradient(90deg,#38E8FF 0%,#7C3AED 100%) !important;
    height: 4px !important;
    border-radius: 4px !important;
    border: none !important;
}}

input[type=range]::-webkit-slider-thumb {{
    -webkit-appearance: none !important;
    width: 18px !important; height: 18px !important;
    border-radius: 50% !important;
    background: #F0F4FF !important;
    box-shadow: 0 0 8px rgba(56,232,255,0.75), 0 0 16px rgba(124,58,237,0.45) !important;
    cursor: pointer !important;
    transition: box-shadow 0.22s !important;
}}

input[type=range]::-webkit-slider-thumb:hover {{
    box-shadow: 0 0 14px rgba(56,232,255,1.0), 0 0 26px rgba(124,58,237,0.75) !important;
}}

input[type=range]::-moz-range-thumb {{
    width: 18px !important; height: 18px !important;
    border-radius: 50% !important; border: none !important;
    background: #F0F4FF !important;
    box-shadow: 0 0 8px rgba(56,232,255,0.75), 0 0 16px rgba(124,58,237,0.45) !important;
    cursor: pointer !important;
}}

/* GPU textbox */
#TxtGPU textarea {{
    background: rgba(56,232,255,0.04) !important;
    border-color: rgba(56,232,255,0.26) !important;
    color: #38E8FF !important;
    font-size: 0.82rem !important;
}}

/* Upload area inner text */
.upload-container span, .file-preview-holder span,
[data-testid="image"] .wrap span {{ color: #8FA8C8 !important; }}

/* Page visibility */
#page-about:not(.imageshield-visible),
#page-main.imageshield-hidden {{
    display: none !important;
}}
#page-about.imageshield-visible {{
    display: flex !important;
}}
#page-main.imageshield-visible {{
    display: block !important;
}}

/* About page — typography (mirrors Home page colour system) */
#page-about .prose h1,
#page-about .prose .h1 {{
    font-size: 1.72rem !important;
    font-weight: 800 !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    letter-spacing: 0.02em !important;
    background: linear-gradient(90deg, #38E8FF 0%, #A78BFA 60%, #6EE7FF 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
    line-height: 1.35 !important;
    margin-bottom: 0.5rem !important;
}}
#page-about .prose h2,
#page-about .prose .h2 {{
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    color: #38E8FF !important;
    -webkit-text-fill-color: #38E8FF !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    margin-top: 1.4rem !important;
    margin-bottom: 0.45rem !important;
}}
#page-about .prose h3,
#page-about .prose .h3 {{
    font-size: 0.97rem !important;
    font-weight: 700 !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    color: #A78BFA !important;
    -webkit-text-fill-color: #A78BFA !important;
    letter-spacing: 0.04em !important;
    margin-top: 1rem !important;
    margin-bottom: 0.35rem !important;
}}
#page-about .prose,
#page-about .prose p,
#page-about .prose li,
#page-about .prose ul,
#page-about .prose ol {{
    color: #8FA8C8 !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    font-size: 0.92rem !important;
    line-height: 1.75 !important;
    -webkit-text-fill-color: #8FA8C8 !important;
}}
#page-about .prose strong,
#page-about strong {{
    color: #F0F4FF !important;
    -webkit-text-fill-color: #F0F4FF !important;
    font-weight: 700 !important;
}}
#page-about .prose u {{
    text-decoration-color: rgba(56,232,255,0.55) !important;
    text-underline-offset: 3px !important;
}}
#page-about .prose hr,
#page-about hr {{
    border: none !important;
    border-top: 1px solid rgba(56,232,255,0.16) !important;
    margin: 1.4rem 0 !important;
}}
#page-about .prose a,
#page-about a:not([onclick]) {{
    color: #38E8FF !important;
    -webkit-text-fill-color: #38E8FF !important;
    text-decoration: underline !important;
    text-decoration-color: rgba(56,232,255,0.40) !important;
    text-underline-offset: 3px !important;
}}
#page-about .prose a:hover,
#page-about a:not([onclick]):hover {{
    color: #6EE7FF !important;
    -webkit-text-fill-color: #6EE7FF !important;
    text-decoration-color: rgba(110,231,255,0.65) !important;
}}
#page-about .prose code,
#page-about code {{
    color: #38E8FF !important;
    -webkit-text-fill-color: #38E8FF !important;
    background: rgba(56,232,255,0.10) !important;
    border: 1px solid rgba(56,232,255,0.20) !important;
    padding: 1px 6px !important;
    border-radius: 5px !important;
    font-size: 0.85em !important;
}}

/* About page — reading-column layout / spacing
   NOTE: #page-about is a flex column wrapper with no visible border.
   The actual glowing glass cards are the inner .block children
   (one per gr.Markdown / gr.HTML call). Padding must target those. */

/* Column: constrain to reading width, centre it, gap between cards */
#page-about {{
    max-width: 860px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding: 0 !important;
    box-sizing: border-box !important;
    flex-direction: column !important;
    gap: 12px !important;
}}

/* Glass cards inside the column: generous, balanced inset */
#page-about .block {{
    padding: 2.2rem 2.8rem 2.4rem !important;
    border-radius: 18px !important;
}}

/* Prose: block padding already handles inset — zero prose's own offsets */
#page-about .prose {{
    padding: 0 !important;
    margin: 0 !important;
}}

/* Paragraph & list breathing room */
#page-about .prose p {{
    margin-top: 0 !important;
    margin-bottom: 0.85rem !important;
}}
#page-about .prose li {{
    margin-bottom: 0.4rem !important;
}}
#page-about .prose ul,
#page-about .prose ol {{
    padding-left: 1.4rem !important;
    margin-top: 0.2rem !important;
    margin-bottom: 0.85rem !important;
}}

/* h1 at top of card — block padding provides the top gap; suppress browser default */
#page-about .prose h1:first-child,
#page-about .prose > h1:first-of-type {{
    margin-top: 0 !important;
    padding-top: 0 !important;
}}

/* Back-button card: minimal, compact */
#page-about .block:last-child {{
    padding: 1.2rem 2.8rem !important;
}}

/* Tablet */
@media (max-width: 960px) {{
    #page-about .block {{
        padding: 1.8rem 1.8rem 2rem !important;
    }}
    #page-about .block:last-child {{
        padding: 1rem 1.8rem !important;
    }}
}}

/* Mobile */
@media (max-width: 640px) {{
    #page-about {{
        max-width: 100% !important;
        gap: 8px !important;
    }}
    #page-about .block {{
        padding: 1.4rem 1.2rem 1.6rem !important;
        border-radius: 12px !important;
    }}
    #page-about .block:last-child {{
        padding: 0.9rem 1.2rem !important;
    }}
}}

/* Progress */
.progress-bar, .progress {{
    background: linear-gradient(90deg,#38E8FF,#7C3AED) !important;
    border-radius: 4px !important;
}}

/* Scrollbar */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: rgba(3,8,18,0.6); border-radius: 3px; }}
::-webkit-scrollbar-thumb {{ background: linear-gradient(180deg,#38E8FF,#7C3AED); border-radius: 3px; }}

/* Animations */
@keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}

/* ── MOTION DESIGN ───────────────────────────────────────────────────── */

/* Card border pulse */
@keyframes borderPulse {{
    0%,100% {{ box-shadow:0 0 16px rgba(56,232,255,0.10),0 0 32px rgba(124,58,237,0.06),0 6px 28px rgba(0,0,0,0.55); }}
    50%     {{ box-shadow:0 0 28px rgba(56,232,255,0.24),0 0 52px rgba(124,58,237,0.14),0 6px 28px rgba(0,0,0,0.55); }}
}}
.block,.form {{
    animation:fadeInUp 0.42s ease both,borderPulse 8s 0.45s ease-in-out infinite !important;
}}

/* Protect button breathing glow */
@keyframes protectGlow {{
    0%,100% {{ box-shadow:0 0 22px rgba(56,232,255,0.38),0 4px 16px rgba(0,0,0,0.42); }}
    50%     {{ box-shadow:0 0 46px rgba(56,232,255,0.74),0 0 26px rgba(124,58,237,0.42),0 6px 20px rgba(0,0,0,0.44); }}
}}
button.primary,#protect_btn button,#protect_btn .lg {{
    animation:protectGlow 3.2s ease-in-out infinite !important;
}}
button.primary:hover,#protect_btn button:hover,#protect_btn .lg:hover {{
    animation:none !important;
    transform:translateY(-2px) scale(1.02) !important;
    box-shadow:0 0 52px rgba(56,232,255,0.82),0 8px 28px rgba(0,0,0,0.52) !important;
    filter:brightness(1.08) !important;
}}

/* Navbar slide-down entrance */
@keyframes navSlideDown {{
    from {{ opacity:0; transform:translateY(-20px); }}
    to   {{ opacity:1; transform:translateY(0); }}
}}
#main-nav {{ animation:navSlideDown 0.55s cubic-bezier(0.16,1,0.3,1) both !important; }}

/* Slider track shimmer */
@keyframes sliderShimmer {{
    from {{ background-position:0% 50%; }}
    to   {{ background-position:100% 50%; }}
}}
input[type=range] {{
    background:linear-gradient(90deg,#7C3AED 0%,#38E8FF 40%,#A78BFA 60%,#7C3AED 100%) !important;
    background-size:200% 100% !important;
    animation:sliderShimmer 3s ease-in-out infinite alternate !important;
    height:4px !important;border-radius:4px !important;border:none !important;
}}

/* Upload corner L-brackets (injected by JS) */
@keyframes cornerBlink {{
    0%,100% {{ opacity:0.38; }}
    50%     {{ opacity:1; }}
}}
.uc {{
    position:absolute;width:14px;height:14px;pointer-events:none;z-index:3;
    animation:cornerBlink 2.4s ease-in-out infinite;
}}
.uc::before,.uc::after {{ content:'';position:absolute;background:#38E8FF;border-radius:1px; }}
.uc::before {{ width:2px;height:14px;top:0;left:0; }}
.uc::after  {{ width:14px;height:2px;top:0;left:0; }}
.uc.tl {{ top:8px;left:8px; }}
.uc.tr {{ top:8px;right:8px;transform:scaleX(-1); }}
.uc.bl {{ bottom:8px;left:8px;transform:scaleY(-1); }}
.uc.br {{ bottom:8px;right:8px;transform:scale(-1);animation-delay:0.6s; }}

/* AI scan line while protecting */
@keyframes scanDown {{
    0%   {{ top:0%;opacity:0; }}
    6%   {{ opacity:1; }}
    94%  {{ opacity:1; }}
    100% {{ top:100%;opacity:0; }}
}}
.is-protecting [data-testid="image"],
.is-protecting .image-container {{
    position:relative !important;overflow:hidden !important;
}}
.is-protecting [data-testid="image"]::after,
.is-protecting .image-container::after {{
    content:'' !important;position:absolute !important;
    left:0;right:0;top:0;height:3px !important;
    background:linear-gradient(90deg,transparent 0%,#38E8FF 35%,#A78BFA 65%,transparent 100%) !important;
    animation:scanDown 2.5s linear infinite !important;
    pointer-events:none !important;z-index:10 !important;
}}

/* Hero shimmer keyframe (applied by JS to h1) */
@keyframes heroShimmer {{
    from {{ background-position:0% 50%; }}
    to   {{ background-position:100% 50%; }}
}}

/* Ambient blob floats */
@keyframes af1 {{ 0%,100% {{ transform:translate(0,0) scale(1); }} 50% {{ transform:translate(34px,-46px) scale(1.06); }} }}
@keyframes af2 {{ 0%,100% {{ transform:translate(0,0) scale(1); }} 50% {{ transform:translate(-30px,38px) scale(0.95); }} }}
@keyframes af3 {{ 0%,100% {{ transform:translate(0,0) scale(1); }} 50% {{ transform:translate(46px,28px) scale(1.04); }} }}
@keyframes af4 {{ 0%,100% {{ transform:translate(0,0) scale(1); }} 50% {{ transform:translate(-36px,-26px) scale(0.97); }} }}
@keyframes af5 {{ 0%,100% {{ transform:translate(0,0) scale(1); }} 50% {{ transform:translate(22px,44px) scale(1.03); }} }}

/* Floating particles (spawned on body by JS) */
@keyframes pRise0 {{ 0%{{transform:translateY(0) translateX(0);opacity:0}} 8%{{opacity:1}} 92%{{opacity:1}} 100%{{transform:translateY(-105vh) translateX(-65px);opacity:0}} }}
@keyframes pRise1 {{ 0%{{transform:translateY(0) translateX(0);opacity:0}} 8%{{opacity:1}} 92%{{opacity:1}} 100%{{transform:translateY(-105vh) translateX(48px);opacity:0}} }}
@keyframes pRise2 {{ 0%{{transform:translateY(0) translateX(0);opacity:0}} 8%{{opacity:1}} 92%{{opacity:1}} 100%{{transform:translateY(-105vh) translateX(-28px);opacity:0}} }}
@keyframes pRise3 {{ 0%{{transform:translateY(0) translateX(0);opacity:0}} 8%{{opacity:1}} 92%{{opacity:1}} 100%{{transform:translateY(-105vh) translateX(72px);opacity:0}} }}

/* Button ripple */
@keyframes rippleOut {{ 0%{{transform:scale(1);opacity:0.55}} 100%{{transform:scale(24);opacity:0}} }}

/* Shield idle pulse */
@keyframes shieldIdlePulse {{
    0%,100% {{ opacity:0.55; filter:drop-shadow(0 0 4px rgba(56,232,255,0.40)); }}
    50%     {{ opacity:0.90; filter:drop-shadow(0 0 10px rgba(56,232,255,0.80)) drop-shadow(0 0 6px rgba(124,58,237,0.50)); }}
}}

/* Background shield float animations */
@keyframes bsFloat1 {{ 0%,100% {{ transform:translate(0,0) rotate(-8deg);  }} 50% {{ transform:translate(18px,-28px) rotate(-5deg);  }} }}
@keyframes bsFloat2 {{ 0%,100% {{ transform:translate(0,0) rotate(12deg);  }} 50% {{ transform:translate(-22px,18px) rotate(10deg);  }} }}
@keyframes bsFloat3 {{ 0%,100% {{ transform:translate(0,0) rotate(-3deg);  }} 50% {{ transform:translate(14px,22px)  rotate(0deg);   }} }}
@keyframes bsFloat4 {{ 0%,100% {{ transform:translate(0,0) rotate(7deg);   }} 50% {{ transform:translate(-14px,-18px) rotate(10deg); }} }}
@keyframes bsFloat5 {{ 0%,100% {{ transform:translate(0,0) rotate(-14deg); }} 50% {{ transform:translate(16px,14px)  rotate(-11deg); }} }}
/* Large background orbital rings */
@keyframes bgOrbSpin1 {{ from {{ transform:rotate(0deg);   }} to {{ transform:rotate(360deg);  }} }}
@keyframes bgOrbSpin2 {{ from {{ transform:rotate(0deg);   }} to {{ transform:rotate(-360deg); }} }}
/* Take the Tour — pulse every 5 s */
@keyframes tourPulse {{
    0%,74%,100% {{ transform:scale(1) translateY(0);       box-shadow:0 0 18px rgba(56,232,255,0.42),0 4px 14px rgba(0,0,0,0.4); }}
    80%         {{ transform:scale(1.06) translateY(-2px);  box-shadow:0 0 36px rgba(56,232,255,0.82),0 0 20px rgba(139,92,246,0.48),0 6px 18px rgba(0,0,0,0.5); }}
}}
#tour-reopen {{ animation:tourPulse 5s ease-in-out infinite !important; }}
#tour-reopen:hover {{ animation:none !important; transform:translateY(-2px) !important; filter:brightness(1.12) !important; }}

/* Collapse purely-decorative Gradio wrappers that hold no UI content.
   These are the .block divs whose children get re-parented to <body> by JS.
   The :has() check prevents accidentally collapsing real content blocks.   */
.gradio-container > .block:has(> #bg-decor),
.gradio-container > .block:has(> #ambient-layer),
.gradio-container > .block:has(> #shield-anim),
.gradio-container > .block:has(> #bg-shields),
.gradio-container > .block:has(> #tour-root) {{
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: hidden !important;
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
}}

/* Reduced motion */
@media (prefers-reduced-motion:reduce) {{
    *,*::before,*::after {{
        animation-duration:0.01ms !important;
        animation-iteration-count:1 !important;
        transition-duration:0.01ms !important;
    }}
}}

/* Layout */
.gradio-row {{ gap: 16px !important; align-items: stretch !important; }}
.gradio-column {{ gap: 14px !important; }}
"""


def cleanup_old_outputs() -> None:
    """Remove generated files older than one day without blocking app startup."""
    cutoff = time.time() - MAX_OUTPUT_AGE_SECONDS
    for path in OUTPUT_DIR.glob("protected-*.png"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            continue


def square_crop_image(image, resolution):
    if image is None:
        return None
    size = int(resolution)
    source = ImageOps.exif_transpose(image).convert("RGB")
    return ImageOps.fit(
        source,
        (size, size),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def store_original_image(image, resolution):
    if image is None:
        return None, None
    return image.copy(), square_crop_image(image, resolution)


def refresh_input_preview(original_image, resolution):
    return square_crop_image(original_image, resolution)


def prereq_gpu(image):
    """Validate input and show the protection device before the run starts."""
    if image is None:
        raise gr.Error("Please upload an image first.")
    from .protection import device_summary

    service = get_service()
    status = f"Processing device: {device_summary(service.device)}"
    return gr.update(value=status, visible=True)


def model(original_image, resolution, pgd_eps, steps, progress=gr.Progress()):
    """Run real ImageShield protection while reporting step progress."""
    if original_image is None:
        raise gr.Error("Please upload an image first.")

    from .protection import ProtectionCancelled, ProtectionSettings

    square_input = square_crop_image(original_image, resolution)
    settings = ProtectionSettings(
        resolution=int(resolution),
        eps=float(pgd_eps),
        steps=int(steps),
    )

    try:
        service = get_service()
        progress(0, desc="Loading the offline protection model")
        protected_image = service.protect(
            square_input,
            settings=settings,
            progress=lambda value, description: progress(value, desc=description),
        )
    except ProtectionCancelled:
        raise gr.Error("Protection stopped.")
    except Exception as exc:
        raise gr.Error(f"Protection failed: {exc}") from exc

    output_path = OUTPUT_DIR / f"protected-{uuid.uuid4().hex}.png"
    protected_image.save(output_path, format="PNG")
    return protected_image, gr.update(
        label=Path(output_path).name,
        value=str(output_path),
        visible=True,
    )


def stop_protection():
    if SERVICE is not None:
        SERVICE.cancel()
    return gr.update(
        value="Stopping protection after the current optimization step...",
        visible=True,
    )


# ---------------------------------------------------------------------------
# Decorative background — fixed bottom-right
# ---------------------------------------------------------------------------
BG_DECOR_HTML = """
<div id="bg-decor" aria-hidden="true" style="
    position:fixed; bottom:0; right:0; width:750px; height:700px;
    pointer-events:none; z-index:0; overflow:hidden;">
  <svg width="750" height="700" viewBox="0 0 750 700"
       fill="none" xmlns="http://www.w3.org/2000/svg"
       style="position:absolute;right:0;bottom:0;">
    <style>
      @keyframes sp{0%{stroke-dashoffset:950;opacity:0}8%{opacity:.20}92%{opacity:.20}100%{stroke-dashoffset:0;opacity:0}}
      @keyframes dp{0%,100%{opacity:.45}50%{opacity:1}}
      .sp1{stroke-dasharray:950;animation:sp 9s .4s linear infinite}
      .sp2{stroke-dasharray:950;animation:sp 9s 3.4s linear infinite}
      .sp3{stroke-dasharray:950;animation:sp 9s 6.4s linear infinite}
      .dp1{animation:dp 2.8s 0.0s ease-in-out infinite}
      .dp2{animation:dp 2.8s 0.4s ease-in-out infinite}
      .dp3{animation:dp 2.8s 0.8s ease-in-out infinite}
      .dp4{animation:dp 2.8s 1.2s ease-in-out infinite}
      .dp5{animation:dp 2.8s 1.6s ease-in-out infinite}
      .dp6{animation:dp 2.8s 2.0s ease-in-out infinite}
      .dp7{animation:dp 2.8s 2.4s ease-in-out infinite}
    </style>
    <defs>
      <radialGradient id="bG1" cx="65%" cy="72%" r="50%">
        <stop offset="0%" stop-color="#38E8FF" stop-opacity="0.13"/>
        <stop offset="100%" stop-color="#38E8FF" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="bG2" cx="55%" cy="85%" r="50%">
        <stop offset="0%" stop-color="#7C3AED" stop-opacity="0.11"/>
        <stop offset="100%" stop-color="#7C3AED" stop-opacity="0"/>
      </radialGradient>
    </defs>
    <ellipse cx="620" cy="620" rx="390" ry="290" stroke="rgba(56,232,255,0.055)" stroke-width="1" fill="none"/>
    <ellipse cx="620" cy="620" rx="290" ry="210" stroke="rgba(124,58,237,0.07)"  stroke-width="1" fill="none"/>
    <ellipse cx="620" cy="620" rx="195" ry="145" stroke="rgba(56,232,255,0.048)" stroke-width="1" fill="none"/>
    <ellipse cx="620" cy="620" rx="105" ry="80"  stroke="rgba(124,58,237,0.055)" stroke-width="1" fill="none"/>
    <path class="sp1" d="M 180 700 C 380 590 540 440 750 310" stroke="rgba(56,232,255,0.16)"  stroke-width="1.5" fill="none"/>
    <path class="sp2" d="M  80 700 C 340 540 520 370 750 210" stroke="rgba(124,58,237,0.14)" stroke-width="1.2" fill="none"/>
    <path class="sp3" d="M 290 700 C 470 610 610 510 750 415" stroke="rgba(56,232,255,0.12)"  stroke-width="1.2" fill="none"/>
    <path d="M 410 700 C 540 645 650 570 750 500" stroke="rgba(168,85,247,0.055)" stroke-width="0.8" fill="none"/>
    <path d="M 520 700 C 610 670 690 630 750 590" stroke="rgba(56,232,255,0.04)"  stroke-width="0.7" fill="none"/>
    <ellipse cx="670" cy="650" rx="270" ry="210" fill="url(#bG1)"/>
    <ellipse cx="530" cy="690" rx="210" ry="165" fill="url(#bG2)"/>
    <circle class="dp1" cx="500" cy="390" r="2.5" fill="rgba(56,232,255,0.52)"/>
    <circle class="dp2" cx="548" cy="432" r="1.8" fill="rgba(56,232,255,0.44)"/>
    <circle class="dp3" cx="592" cy="402" r="2.2" fill="rgba(56,232,255,0.38)"/>
    <circle class="dp4" cx="638" cy="366" r="1.8" fill="rgba(56,232,255,0.28)"/>
    <circle class="dp5" cx="564" cy="488" r="2.0" fill="rgba(124,58,237,0.52)"/>
    <circle class="dp6" cx="612" cy="508" r="2.5" fill="rgba(124,58,237,0.40)"/>
    <circle class="dp7" cx="662" cy="460" r="1.8" fill="rgba(124,58,237,0.28)"/>
    <line x1="476" y1="353" x2="486" y2="363" stroke="rgba(56,232,255,0.28)" stroke-width="1"/>
    <line x1="486" y1="353" x2="476" y2="363" stroke="rgba(56,232,255,0.28)" stroke-width="1"/>
    <line x1="682" y1="374" x2="690" y2="382" stroke="rgba(56,232,255,0.18)" stroke-width="1"/>
    <line x1="690" y1="374" x2="682" y2="382" stroke="rgba(56,232,255,0.18)" stroke-width="1"/>
  </svg>
</div>
"""

# ---------------------------------------------------------------------------
# Ambient floating glow layer — aurora blobs behind content
# ---------------------------------------------------------------------------
AMBIENT_HTML = """
<div id="ambient-layer" aria-hidden="true" style="
    position:fixed;inset:0;pointer-events:none;z-index:0;overflow:hidden;">
  <div style="position:absolute;top:7%;left:3%;width:420px;height:420px;border-radius:50%;
              background:radial-gradient(circle,rgba(56,232,255,0.072) 0%,transparent 70%);
              filter:blur(60px);animation:af1 30s ease-in-out infinite;"></div>
  <div style="position:absolute;bottom:8%;right:5%;width:500px;height:500px;border-radius:50%;
              background:radial-gradient(circle,rgba(124,58,237,0.068) 0%,transparent 70%);
              filter:blur(70px);animation:af2 36s ease-in-out infinite;"></div>
  <div style="position:absolute;top:42%;right:10%;width:280px;height:280px;border-radius:50%;
              background:radial-gradient(circle,rgba(56,232,255,0.052) 0%,transparent 70%);
              filter:blur(50px);animation:af3 24s ease-in-out infinite;animation-delay:-9s;"></div>
  <div style="position:absolute;top:4%;right:22%;width:340px;height:340px;border-radius:50%;
              background:radial-gradient(circle,rgba(167,139,250,0.058) 0%,transparent 70%);
              filter:blur(65px);animation:af4 40s ease-in-out infinite;animation-delay:-16s;"></div>
  <div style="position:absolute;bottom:22%;left:14%;width:260px;height:260px;border-radius:50%;
              background:radial-gradient(circle,rgba(56,232,255,0.042) 0%,transparent 70%);
              filter:blur(48px);animation:af5 32s ease-in-out infinite;animation-delay:-6s;"></div>
</div>
"""

# ---------------------------------------------------------------------------
# Animated shield — SafeShot-style orbiting energy ring illustration
# ---------------------------------------------------------------------------
SHIELD_ANIM_HTML = """
<div id="shield-anim" aria-hidden="true" style="
    position:fixed;top:14px;left:50%;
    transform:translateX(-50%);
    width:440px;height:440px;
    pointer-events:none;z-index:0;opacity:0.62;">
  <svg width="440" height="440" viewBox="-130 -130 260 260"
       xmlns="http://www.w3.org/2000/svg" overflow="visible">
    <style>
      /* Shield float */
      #sg { animation:sgFloat 7s ease-in-out infinite; }
      /* Orbit ring spins with 3-D skew baked into keyframes */
      #og { animation:ogSpin 10s linear infinite;
            transform-box:fill-box; transform-origin:50% 50%; }
      /* Particles twinkle (delays set inline) */
      .pt { animation:ptWink 2.8s ease-in-out infinite; }
      /* Pulse rings (delays set inline) */
      .pr { animation:prPulse 6s ease-out infinite;
            transform-box:fill-box; transform-origin:50% 50%; }

      @keyframes sgFloat {
        0%,100% { transform:translateY(0px);  }
        50%     { transform:translateY(-9px); }
      }
      @keyframes ogSpin {
        from { transform:skewX(-18deg) rotate(  0deg); }
        to   { transform:skewX(-18deg) rotate(360deg); }
      }
      @keyframes ptWink {
        0%,100% { opacity:0.28; }
        50%     { opacity:1.00; }
      }
      @keyframes prPulse {
        0%   { transform:scale(1.0); opacity:0.60; }
        100% { transform:scale(2.6); opacity:0.00; }
      }
      @media (prefers-reduced-motion:reduce) {
        #sg,#og,.pt,.pr { animation:none !important; }
      }
    </style>
    <defs>
      <radialGradient id="saAura" cx="50%" cy="50%" r="55%">
        <stop offset="0%"   stop-color="#1040CC" stop-opacity="0.22"/>
        <stop offset="55%"  stop-color="#38E8FF" stop-opacity="0.07"/>
        <stop offset="100%" stop-color="#38E8FF" stop-opacity="0.00"/>
      </radialGradient>
      <linearGradient id="saBody" x1="25%" y1="0%" x2="75%" y2="100%">
        <stop offset="0%"   stop-color="#1B5EEA" stop-opacity="0.96"/>
        <stop offset="45%"  stop-color="#0C1D60" stop-opacity="0.98"/>
        <stop offset="100%" stop-color="#420E8A" stop-opacity="0.96"/>
      </linearGradient>
      <linearGradient id="saEdge" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%"   stop-color="#38E8FF"/>
        <stop offset="100%" stop-color="#8B5CF6"/>
      </linearGradient>
      <!-- Soft 3px glow -->
      <filter id="saG3" x="-60%" y="-60%" width="220%" height="220%">
        <feGaussianBlur stdDeviation="3" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <!-- Diffuse 8px glow -->
      <filter id="saG8" x="-80%" y="-80%" width="260%" height="260%">
        <feGaussianBlur stdDeviation="8" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
    </defs>

    <!-- Background aura glow -->
    <circle cx="0" cy="0" r="120" fill="url(#saAura)"/>

    <!-- Pulse waves — three rings that expand and fade every 6 s, staggered 2 s apart -->
    <circle class="pr" style="animation-delay:0s"
            cx="0" cy="0" r="50" fill="none"
            stroke="rgba(56,232,255,0.55)" stroke-width="1.6"/>
    <circle class="pr" style="animation-delay:2s"
            cx="0" cy="0" r="50" fill="none"
            stroke="rgba(56,232,255,0.55)" stroke-width="1.6"/>
    <circle class="pr" style="animation-delay:4s"
            cx="0" cy="0" r="50" fill="none"
            stroke="rgba(139,92,246,0.50)" stroke-width="1.4"/>

    <!-- Orbital ring (skewed ellipse that rotates around the shield) -->
    <g id="og">
      <!-- Ghost base — very faint -->
      <ellipse cx="0" cy="0" rx="82" ry="26"
               fill="none" stroke="rgba(56,232,255,0.10)" stroke-width="1.0"/>
      <!-- Bright cyan arc (≈ 68 units of 258-unit perimeter) -->
      <ellipse cx="0" cy="0" rx="82" ry="26" fill="none"
               stroke="rgba(56,232,255,0.82)" stroke-width="2.2"
               stroke-dasharray="68 188" stroke-linecap="round"
               filter="url(#saG3)"/>
      <!-- Purple arc, offset 180° -->
      <ellipse cx="0" cy="0" rx="82" ry="26" fill="none"
               stroke="rgba(139,92,246,0.72)" stroke-width="1.8"
               stroke-dasharray="44 212" stroke-dashoffset="-130"
               stroke-linecap="round" filter="url(#saG3)"/>
      <!-- Particles at ellipse positions: (82·cos θ, 26·sin θ) for θ = 0°…315° -->
      <circle class="pt" style="animation-delay:0.0s;animation-duration:2.4s"
              cx=" 82" cy="  0" r="4.0" fill="#38E8FF" filter="url(#saG3)"/>
      <circle class="pt" style="animation-delay:0.5s;animation-duration:3.0s"
              cx=" 58" cy=" 18" r="2.5" fill="#38E8FF"/>
      <circle class="pt" style="animation-delay:1.0s;animation-duration:2.6s"
              cx="  0" cy=" 26" r="3.0" fill="#38E8FF" filter="url(#saG3)" opacity="0.85"/>
      <circle class="pt" style="animation-delay:1.5s;animation-duration:3.2s"
              cx="-58" cy=" 18" r="2.2" fill="#8B5CF6" opacity="0.80"/>
      <circle class="pt" style="animation-delay:0.3s;animation-duration:2.8s"
              cx="-82" cy="  0" r="3.5" fill="#8B5CF6" filter="url(#saG3)"/>
      <circle class="pt" style="animation-delay:0.8s;animation-duration:2.4s"
              cx="-58" cy="-18" r="2.0" fill="#8B5CF6" opacity="0.70"/>
      <circle class="pt" style="animation-delay:1.3s;animation-duration:3.0s"
              cx="  0" cy="-26" r="2.6" fill="#38E8FF" opacity="0.80"/>
      <circle class="pt" style="animation-delay:1.8s;animation-duration:2.6s"
              cx=" 58" cy="-18" r="2.0" fill="#38E8FF" opacity="0.55"/>
    </g>

    <!-- Shield (floats up/down slowly) -->
    <g id="sg">
      <!-- Wide diffuse halo -->
      <path d="M0-57 L46-41 L46-9 C46 24 25 39 0 47 C-25 39-46 24-46-9 L-46-41 Z"
            fill="rgba(56,232,255,0.04)" filter="url(#saG8)"/>
      <!-- Shield body -->
      <path d="M0-52 L41-37 L41-8 C41 21 23 34 0 42 C-23 34-41 21-41-8 L-41-37 Z"
            fill="url(#saBody)" stroke="url(#saEdge)" stroke-width="2.2"/>
      <!-- Inner chamfer line -->
      <path d="M0-44 L34-31 L34-5 C34 17 18 28 0 35 C-18 28-34 17-34-5 L-34-31 Z"
            fill="none" stroke="rgba(56,232,255,0.30)" stroke-width="0.9"/>
      <!-- Top accent bar -->
      <line x1="-22" y1="-42" x2="22" y2="-42"
            stroke="rgba(56,232,255,0.56)" stroke-width="0.9"/>
      <!-- Corner tick marks -->
      <line x1="-39" y1="-32" x2="-33" y2="-36"
            stroke="rgba(56,232,255,0.42)" stroke-width="0.8"/>
      <line x1=" 33" y1="-36" x2=" 39" y2="-32"
            stroke="rgba(56,232,255,0.42)" stroke-width="0.8"/>
      <!-- Outer lens ring -->
      <circle cx="0" cy="-3" r="21"
              fill="rgba(3,6,26,0.90)" stroke="rgba(56,232,255,0.68)"
              stroke-width="1.7" filter="url(#saG3)"/>
      <!-- Dashed inner track -->
      <circle cx="0" cy="-3" r="14" fill="none"
              stroke="rgba(56,232,255,0.22)" stroke-width="0.8"
              stroke-dasharray="3.5 3.5"/>
      <!-- Purple iris -->
      <circle cx="0" cy="-3" r="9.5"
              fill="rgba(100,28,158,0.60)" stroke="rgba(139,92,246,0.60)"
              stroke-width="1.1"/>
      <!-- Bright core (camera dot) -->
      <circle cx="0" cy="-3" r="5.2" fill="#38E8FF" opacity="0.92"
              filter="url(#saG3)"/>
      <!-- Specular reflections -->
      <circle cx="-5" cy="-8" r="2.0" fill="rgba(255,255,255,0.80)"/>
      <circle cx=" 3" cy=" 0" r="1.1" fill="rgba(255,255,255,0.40)"/>
      <!-- Bottom 3-dot accent -->
      <circle cx="-7" cy="29" r="1.4" fill="rgba(56,232,255,0.55)"/>
      <circle cx=" 0" cy="31" r="1.4" fill="rgba(56,232,255,0.82)"/>
      <circle cx=" 7" cy="29" r="1.4" fill="rgba(56,232,255,0.55)"/>
    </g>

  </svg>
</div>
"""

# ---------------------------------------------------------------------------
# Holographic background shields + large orbital rings
# ---------------------------------------------------------------------------
BG_SHIELDS_HTML = """
<div id="bg-shields" aria-hidden="true" style="
    position:fixed;inset:0;pointer-events:none;z-index:0;overflow:hidden;">

  <!-- Shield 1: Top-left, large, cyan -->
  <div style="position:absolute;top:5%;left:0%;width:320px;height:381px;
              opacity:0.20;filter:blur(1px);
              animation:bsFloat1 32s ease-in-out infinite;">
    <svg viewBox="-55 -65 110 130" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
      <path d="M0-60 L50-43 L50-12 C50 27 28 44 0 54 C-28 44-50 27-50-12 L-50-43 Z"
            fill="rgba(7,18,38,0.40)" stroke="rgba(56,232,255,0.70)" stroke-width="1.8"/>
      <path d="M0-50 L40-36 L40-9 C40 21 22 35 0 43 C-22 35-40 21-40-9 L-40-36 Z"
            fill="none" stroke="rgba(56,232,255,0.28)" stroke-width="0.8"/>
      <line x1="-24" y1="-57" x2="24" y2="-57" stroke="rgba(56,232,255,0.40)" stroke-width="1"/>
      <line x1="-49" y1="-37" x2="-40" y2="-42" stroke="rgba(56,232,255,0.45)" stroke-width="1.2"/>
      <line x1="40" y1="-42" x2="49" y2="-37" stroke="rgba(56,232,255,0.45)" stroke-width="1.2"/>
      <ellipse cx="0" cy="-5" rx="32" ry="10" fill="none" stroke="rgba(56,232,255,0.30)"
               stroke-width="0.8" stroke-dasharray="10 8"/>
      <circle cx="0" cy="-5" r="21" fill="rgba(3,6,26,0.60)" stroke="rgba(56,232,255,0.55)" stroke-width="1.3"/>
      <circle cx="0" cy="-5" r="13" fill="rgba(100,28,158,0.30)" stroke="rgba(139,92,246,0.40)" stroke-width="0.9"/>
      <circle cx="0" cy="-5" r="6"  fill="rgba(56,232,255,0.22)" stroke="rgba(56,232,255,0.55)" stroke-width="0.7"/>
      <circle cx="-2" cy="-7" r="2.2" fill="rgba(255,255,255,0.75)"/>
      <circle cx="-8" cy="41" r="1.8" fill="rgba(56,232,255,0.70)"/>
      <circle cx="0"  cy="43" r="1.8" fill="rgba(56,232,255,0.88)"/>
      <circle cx="8"  cy="41" r="1.8" fill="rgba(56,232,255,0.70)"/>
    </svg>
  </div>

  <!-- Shield 2: Top-right, large, purple tint, blurry -->
  <div style="position:absolute;top:2%;right:2%;width:285px;height:339px;
              opacity:0.16;filter:blur(2px);
              animation:bsFloat2 44s ease-in-out infinite;animation-delay:-10s;">
    <svg viewBox="-55 -65 110 130" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
      <path d="M0-60 L50-43 L50-12 C50 27 28 44 0 54 C-28 44-50 27-50-12 L-50-43 Z"
            fill="rgba(50,10,80,0.40)" stroke="rgba(139,92,246,0.72)" stroke-width="1.8"/>
      <path d="M0-50 L40-36 L40-9 C40 21 22 35 0 43 C-22 35-40 21-40-9 L-40-36 Z"
            fill="none" stroke="rgba(139,92,246,0.28)" stroke-width="0.8"/>
      <line x1="-24" y1="-57" x2="24" y2="-57" stroke="rgba(139,92,246,0.40)" stroke-width="1"/>
      <ellipse cx="0" cy="-5" rx="32" ry="10" fill="none" stroke="rgba(139,92,246,0.30)"
               stroke-width="0.8" stroke-dasharray="10 8"/>
      <circle cx="0" cy="-5" r="21" fill="rgba(3,6,26,0.60)" stroke="rgba(139,92,246,0.55)" stroke-width="1.3"/>
      <circle cx="0" cy="-5" r="13" fill="rgba(100,28,158,0.32)" stroke="rgba(56,232,255,0.40)" stroke-width="0.9"/>
      <circle cx="0" cy="-5" r="6"  fill="rgba(139,92,246,0.22)" stroke="rgba(139,92,246,0.55)" stroke-width="0.7"/>
      <circle cx="-8" cy="41" r="1.8" fill="rgba(139,92,246,0.70)"/>
      <circle cx="0"  cy="43" r="1.8" fill="rgba(139,92,246,0.88)"/>
      <circle cx="8"  cy="41" r="1.8" fill="rgba(139,92,246,0.70)"/>
    </svg>
  </div>

  <!-- Shield 3: Middle-left, medium, cyan -->
  <div style="position:absolute;top:42%;left:2%;width:220px;height:262px;
              opacity:0.16;filter:blur(1px);
              animation:bsFloat3 28s ease-in-out infinite;animation-delay:-5s;">
    <svg viewBox="-55 -65 110 130" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
      <path d="M0-60 L50-43 L50-12 C50 27 28 44 0 54 C-28 44-50 27-50-12 L-50-43 Z"
            fill="rgba(7,18,38,0.40)" stroke="rgba(56,232,255,0.65)" stroke-width="1.8"/>
      <path d="M0-50 L40-36 L40-9 C40 21 22 35 0 43 C-22 35-40 21-40-9 L-40-36 Z"
            fill="none" stroke="rgba(56,232,255,0.25)" stroke-width="0.8"/>
      <ellipse cx="0" cy="-5" rx="32" ry="10" fill="none" stroke="rgba(56,232,255,0.28)"
               stroke-width="0.7" stroke-dasharray="8 7"/>
      <circle cx="0" cy="-5" r="21" fill="rgba(3,6,26,0.60)" stroke="rgba(56,232,255,0.50)" stroke-width="1.2"/>
      <circle cx="0" cy="-5" r="13" fill="rgba(100,28,158,0.28)" stroke="rgba(139,92,246,0.38)" stroke-width="0.8"/>
      <circle cx="0" cy="-5" r="6"  fill="rgba(56,232,255,0.20)" stroke="rgba(56,232,255,0.50)" stroke-width="0.6"/>
      <circle cx="0" cy="43" r="1.8" fill="rgba(56,232,255,0.85)"/>
    </svg>
  </div>

  <!-- Shield 4: Middle-right, large, purple -->
  <div style="position:absolute;top:35%;right:1%;width:290px;height:345px;
              opacity:0.18;filter:blur(1.5px);
              animation:bsFloat4 38s ease-in-out infinite;animation-delay:-14s;">
    <svg viewBox="-55 -65 110 130" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
      <path d="M0-60 L50-43 L50-12 C50 27 28 44 0 54 C-28 44-50 27-50-12 L-50-43 Z"
            fill="rgba(50,10,80,0.35)" stroke="rgba(139,92,246,0.68)" stroke-width="1.8"/>
      <path d="M0-50 L40-36 L40-9 C40 21 22 35 0 43 C-22 35-40 21-40-9 L-40-36 Z"
            fill="none" stroke="rgba(139,92,246,0.26)" stroke-width="0.8"/>
      <line x1="-24" y1="-57" x2="24" y2="-57" stroke="rgba(139,92,246,0.38)" stroke-width="0.9"/>
      <line x1="-49" y1="-37" x2="-40" y2="-42" stroke="rgba(139,92,246,0.42)" stroke-width="1"/>
      <line x1="40" y1="-42" x2="49" y2="-37" stroke="rgba(139,92,246,0.42)" stroke-width="1"/>
      <ellipse cx="0" cy="-5" rx="32" ry="10" fill="none" stroke="rgba(139,92,246,0.28)"
               stroke-width="0.7" stroke-dasharray="9 7"/>
      <circle cx="0" cy="-5" r="21" fill="rgba(3,6,26,0.60)" stroke="rgba(139,92,246,0.50)" stroke-width="1.2"/>
      <circle cx="0" cy="-5" r="13" fill="rgba(100,28,158,0.30)" stroke="rgba(56,232,255,0.38)" stroke-width="0.8"/>
      <circle cx="0" cy="-5" r="6"  fill="rgba(139,92,246,0.20)" stroke="rgba(139,92,246,0.50)" stroke-width="0.6"/>
      <circle cx="-8" cy="41" r="1.8" fill="rgba(139,92,246,0.68)"/>
      <circle cx="0"  cy="43" r="1.8" fill="rgba(139,92,246,0.85)"/>
      <circle cx="8"  cy="41" r="1.8" fill="rgba(139,92,246,0.68)"/>
    </svg>
  </div>

  <!-- Shield 5: Bottom-left, medium, crisp -->
  <div style="position:absolute;bottom:6%;left:6%;width:195px;height:232px;
              opacity:0.22;filter:blur(0.5px);
              animation:bsFloat5 22s ease-in-out infinite;animation-delay:-3s;">
    <svg viewBox="-55 -65 110 130" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
      <path d="M0-60 L50-43 L50-12 C50 27 28 44 0 54 C-28 44-50 27-50-12 L-50-43 Z"
            fill="rgba(7,18,38,0.42)" stroke="rgba(56,232,255,0.78)" stroke-width="2"/>
      <path d="M0-50 L40-36 L40-9 C40 21 22 35 0 43 C-22 35-40 21-40-9 L-40-36 Z"
            fill="none" stroke="rgba(56,232,255,0.32)" stroke-width="0.9"/>
      <line x1="-24" y1="-57" x2="24" y2="-57" stroke="rgba(56,232,255,0.50)" stroke-width="1.1"/>
      <circle cx="0" cy="-5" r="21" fill="rgba(3,6,26,0.65)" stroke="rgba(56,232,255,0.62)" stroke-width="1.4"/>
      <circle cx="0" cy="-5" r="13" fill="rgba(100,28,158,0.35)" stroke="rgba(139,92,246,0.48)" stroke-width="1"/>
      <circle cx="0" cy="-5" r="6"  fill="rgba(56,232,255,0.25)" stroke="rgba(56,232,255,0.62)" stroke-width="0.8"/>
      <circle cx="-1.5" cy="-7" r="2.2" fill="rgba(255,255,255,0.80)"/>
      <circle cx="0"    cy="43" r="1.8" fill="rgba(56,232,255,0.90)"/>
    </svg>
  </div>

  <!-- Large orbital ring 1: Left-center, slow cyan rotation -->
  <div style="position:absolute;top:18%;left:-95px;width:460px;height:265px;
              opacity:0.10;animation:bgOrbSpin1 22s linear infinite;">
    <svg viewBox="0 0 390 225" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
      <ellipse cx="195" cy="112" rx="188" ry="106"
               fill="none" stroke="rgba(56,232,255,0.90)" stroke-width="1.5"
               stroke-dasharray="30 22"/>
      <ellipse cx="195" cy="112" rx="145" ry="82"
               fill="none" stroke="rgba(56,232,255,0.50)" stroke-width="0.8"
               stroke-dasharray="14 26"/>
      <circle cx="383" cy="112" r="4"   fill="rgba(56,232,255,0.90)"/>
      <circle cx="7"   cy="112" r="3"   fill="rgba(56,232,255,0.70)"/>
      <circle cx="195" cy="6"   r="3.5" fill="rgba(56,232,255,0.65)"/>
    </svg>
  </div>

  <!-- Large orbital ring 2: Bottom-center, slow purple counter-rotation -->
  <div style="position:absolute;bottom:3%;left:25%;width:420px;height:235px;
              opacity:0.09;animation:bgOrbSpin2 28s linear infinite;animation-delay:-7s;">
    <svg viewBox="0 0 350 196" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
      <ellipse cx="175" cy="98" rx="168" ry="91"
               fill="none" stroke="rgba(139,92,246,0.90)" stroke-width="1.5"
               stroke-dasharray="26 18"/>
      <ellipse cx="175" cy="98" rx="125" ry="68"
               fill="none" stroke="rgba(139,92,246,0.50)" stroke-width="0.8"
               stroke-dasharray="12 22"/>
      <circle cx="343" cy="98" r="3.5" fill="rgba(139,92,246,0.90)"/>
      <circle cx="7"   cy="98" r="2.5" fill="rgba(139,92,246,0.70)"/>
    </svg>
  </div>

</div>
"""

# ---------------------------------------------------------------------------
# Navigation bar
# ---------------------------------------------------------------------------
NAV_HTML = """
<div id="main-nav" style="
    display:flex; justify-content:space-between; align-items:center;
    padding:13px 26px;
    background:rgba(6,14,28,0.92);
    border-radius:18px;
    border:1px solid rgba(56,232,255,0.40);
    margin-bottom:20px;
    box-shadow:0 0 20px rgba(56,232,255,0.12),0 8px 30px rgba(0,0,0,0.55);
    backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px);
    font-family:'Inter',system-ui,sans-serif;">
  <div style="display:flex;align-items:center;gap:12px;">
    <svg width="38" height="44" viewBox="-20 -23 40 47" xmlns="http://www.w3.org/2000/svg"
         style="flex-shrink:0;filter:drop-shadow(0 0 6px rgba(56,232,255,0.60));">
      <path d="M0-22 L17-15 L17-4 C17 9 9 14 0 17 C-9 14-17 9-17-4 L-17-15 Z"
            fill="rgba(10,20,55,0.95)" stroke="rgba(56,232,255,0.90)" stroke-width="1.4"/>
      <path d="M0-18 L13-12 L13-2 C13 6 7 10 0 13 C-7 10-13 6-13-2 L-13-12 Z"
            fill="none" stroke="rgba(56,232,255,0.28)" stroke-width="0.7"/>
      <ellipse cx="0" cy="-2" rx="11" ry="3.5" fill="none"
               stroke="rgba(56,232,255,0.30)" stroke-width="0.6" stroke-dasharray="4 4"/>
      <circle cx="0" cy="-2" r="8"
              fill="rgba(3,6,26,0.90)" stroke="rgba(56,232,255,0.75)" stroke-width="1.1"/>
      <circle cx="0" cy="-2" r="5"
              fill="rgba(100,28,158,0.65)" stroke="rgba(139,92,246,0.60)" stroke-width="0.8"/>
      <circle cx="0" cy="-2" r="2.5" fill="#38E8FF" opacity="0.95"/>
      <circle cx="-1.2" cy="-3.2" r="0.9" fill="rgba(255,255,255,0.88)"/>
    </svg>
    <div>
      <div style="font-size:17px;font-weight:800;color:#38E8FF;
                  letter-spacing:0.12em;text-transform:uppercase;
                  text-shadow:0 0 16px rgba(56,232,255,0.65);
                  line-height:1.2;">SafeShot</div>
      <div style="font-size:10px;font-weight:500;color:rgba(56,232,255,0.50);
                  letter-spacing:0.09em;text-transform:uppercase;line-height:1;">
        AI-Powered Image Protection
      </div>
    </div>
  </div>
  <div style="display:flex;gap:26px;align-items:center;">
    <a onclick="window.showPage('main')" id="nav-home"
       style="cursor:pointer;font-size:14px;font-weight:600;color:#C4D4E4;
              text-decoration:none;padding:5px 2px;
              border-bottom:2px solid transparent;letter-spacing:0.04em;"
       onmouseover="if(this.style.borderBottomColor!='rgb(56, 232, 255)'){this.style.color='#38E8FF';this.style.textShadow='0 0 10px rgba(56,232,255,0.5)';}"
       onmouseout="if(this.style.borderBottomColor!='rgb(56, 232, 255)'){this.style.color='#C4D4E4';this.style.textShadow='none';}">
      Home
    </a>
    <a onclick="window.showPage('about')" id="nav-about"
       style="cursor:pointer;font-size:14px;font-weight:600;color:#C4D4E4;
              text-decoration:none;padding:5px 2px;
              border-bottom:2px solid transparent;letter-spacing:0.04em;"
       onmouseover="if(this.style.borderBottomColor!='rgb(56, 232, 255)'){this.style.color='#38E8FF';this.style.textShadow='0 0 10px rgba(56,232,255,0.5)';}"
       onmouseout="if(this.style.borderBottomColor!='rgb(56, 232, 255)'){this.style.color='#C4D4E4';this.style.textShadow='none';}">
      About
    </a>
  </div>
</div>
"""

# ---------------------------------------------------------------------------
# Spotlight tour overlay
# ---------------------------------------------------------------------------
TOUR_HTML = """
<div id="tour-root">
  <svg id="tour-svg"
       style="display:none;position:fixed;top:0;left:0;
              width:100vw;height:100vh;z-index:10000;pointer-events:none;">
    <defs>
      <mask id="tour-mask">
        <rect width="100%" height="100%" fill="white"/>
        <rect id="tour-hole" rx="10" ry="10" fill="black"/>
      </mask>
    </defs>
    <rect width="100%" height="100%" fill="rgba(2,8,20,0.75)" mask="url(#tour-mask)"/>
  </svg>
  <div id="tour-blocker"
       style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;z-index:9999;"></div>
  <div id="tour-card"
       style="display:none;position:fixed;z-index:10001;
              background:rgba(6,14,28,0.97);
              border-radius:16px;padding:24px;
              max-width:320px;width:min(320px,90vw);
              border:1px solid rgba(56,232,255,0.38);
              box-shadow:0 0 20px rgba(56,232,255,0.14),0 8px 32px rgba(0,0,0,0.78);
              font-family:'Inter',system-ui,sans-serif;
              backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
      <span id="tour-counter"
            style="font-size:11px;font-weight:700;letter-spacing:.08em;
                   color:rgba(56,232,255,0.65);text-transform:uppercase;"></span>
      <button onclick="window.tourFinish()"
              style="background:none;border:none;font-size:22px;cursor:pointer;
                     color:#506070;line-height:1;padding:0;"
              onmouseover="this.style.color='#38E8FF'"
              onmouseout="this.style.color='#506070'">&times;</button>
    </div>
    <h3 id="tour-title"
        style="margin:0 0 8px;font-size:17px;font-weight:700;
               color:#F0F4FF;letter-spacing:0.01em;"></h3>
    <p id="tour-text"
       style="margin:0 0 20px;font-size:14px;line-height:1.65;color:#8FA8C8;"></p>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button id="btn-back" onclick="window.tourBack()"
              style="padding:9px 18px;border-radius:9px;
                     border:1px solid rgba(56,232,255,0.35);
                     background:rgba(56,232,255,0.06);cursor:pointer;
                     font-size:13px;font-weight:600;color:#8FA8C8;"
              onmouseover="this.style.borderColor='rgba(56,232,255,0.7)';this.style.color='#38E8FF';"
              onmouseout="this.style.borderColor='rgba(56,232,255,0.35)';this.style.color='#8FA8C8';">
        Back
      </button>
      <button id="btn-next" onclick="window.tourNext()"
              style="padding:9px 20px;border-radius:9px;border:none;
                     background:linear-gradient(135deg,#00D9FF,#7C3AED);
                     color:#040E1C;cursor:pointer;font-size:13px;font-weight:700;
                     box-shadow:0 0 14px rgba(56,232,255,0.32);"
              onmouseover="this.style.filter='brightness(1.1)'"
              onmouseout="this.style.filter='none'">Next</button>
      <button id="btn-finish" onclick="window.tourFinish()"
              style="display:none;padding:9px 20px;border-radius:9px;border:none;
                     background:linear-gradient(135deg,#00D9FF,#7C3AED);
                     color:#040E1C;cursor:pointer;font-size:13px;font-weight:700;
                     box-shadow:0 0 14px rgba(56,232,255,0.32);"
              onmouseover="this.style.filter='brightness(1.1)'"
              onmouseout="this.style.filter='none'">Finish Tour</button>
    </div>
  </div>
  <button id="tour-reopen" onclick="window.tourStart()"
          style="display:block;position:fixed;bottom:24px;right:24px;z-index:9998;
                 background:linear-gradient(135deg,#00D9FF,#7C3AED);
                 color:#040E1C;border:none;border-radius:50px;padding:11px 22px;
                 font-size:13px;font-weight:700;cursor:pointer;
                 box-shadow:0 0 18px rgba(56,232,255,0.42),0 4px 14px rgba(0,0,0,0.4);
                 font-family:'Inter',system-ui,sans-serif;"
          onmouseover="this.style.filter='brightness(1.1)';this.style.transform='translateY(-2px)';"
          onmouseout="this.style.filter='none';this.style.transform='none';">
    ? Take the Tour
  </button>
</div>
"""

# ---------------------------------------------------------------------------
# JavaScript — runs after Gradio renders
# LAYER 3: Direct DOM manipulation — overrides everything regardless of CSS
# ---------------------------------------------------------------------------
ALL_JS = """
() => {
    // ── LAYER 3: Inject a runtime <style> tag + direct style manipulation ──
    // This is the most reliable override for Gradio's Svelte-compiled styles.

    var runtimeCSS = `
        /* Runtime injected — highest cascade priority */
        .block .label-wrap, .form .label-wrap,
        .block > div > .label-wrap, .wrap > .label-wrap {
            display: inline-flex !important;
            align-items: center !important;
            background: rgba(56,232,255,0.07) !important;
            border: 1px solid rgba(56,232,255,0.42) !important;
            border-radius: 20px !important;
            padding: 3px 12px !important;
            margin-bottom: 10px !important;
            width: auto !important;
            max-width: max-content !important;
        }
        .block .label-wrap span, .block .label-wrap label span,
        .form .label-wrap span, .form .label-wrap label span {
            color: #38E8FF !important;
            -webkit-text-fill-color: #38E8FF !important;
            font-size: 0.72rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.09em !important;
            text-transform: uppercase !important;
            background: none !important;
            -webkit-background-clip: unset !important;
        }
        #hero-header, div#hero-header, #hero-header .block {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            backdrop-filter: none !important;
            -webkit-backdrop-filter: none !important;
        }
        button.primary, button.primary:not(:disabled),
        .primary > button {
            background: linear-gradient(135deg,#00D9FF 0%,#38E8FF 45%,#7C3AED 100%) !important;
            color: #040E1C !important;
            border: none !important;
            font-weight: 700 !important;
            min-height: 52px !important;
        }
        button.stop, button.cancel, button.stop:not(:disabled),
        .stop > button, .cancel > button {
            background: linear-gradient(135deg,#FF8C42 0%,#FF5E5B 100%) !important;
            color: #ffffff !important;
            border: none !important;
            font-weight: 700 !important;
            min-height: 52px !important;
        }
        /* Neutralise the Gradio .block wrapper that contains #tour-root and
           #ambient-layer. backdrop-filter on a parent hijacks position:fixed
           in Chrome, breaking viewport anchoring for all fixed children. */
        #tour-root, #ambient-layer, #shield-anim, #bg-shields, #bg-decor {
            backdrop-filter: none !important;
            -webkit-backdrop-filter: none !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
            animation: none !important;
        }
    `;

    var styleEl = document.createElement('style');
    styleEl.id = 'imageshield-runtime';
    styleEl.textContent = runtimeCSS;
    document.head.appendChild(styleEl);

    function hideUseViaApi() {
        document.querySelectorAll('a, button').forEach(function(el) {
            if (!el.textContent || el.textContent.indexOf('Use via API') === -1) return;
            el.style.setProperty('display', 'none', 'important');
            var next = el.nextSibling;
            if (next && next.nodeType === Node.TEXT_NODE) {
                next.textContent = next.textContent.replace(/^\\s*[·•]\\s*/, ' ');
            } else if (next && next.textContent && /^[\\s·•]+$/.test(next.textContent)) {
                next.style && next.style.setProperty('display', 'none', 'important');
            }
        });
    }
    hideUseViaApi();
    new MutationObserver(hideUseViaApi).observe(document.body, {childList: true, subtree: true});

    // ── Escape backdrop-filter stacking context ────────────────────────────
    // Chrome (and Safari) treat a backdrop-filter on any ancestor as a new
    // "containing block" for position:fixed children, breaking their viewport
    // anchoring.  Gradio's .block wrapper around gr.HTML(TOUR_HTML) gets our
    // backdrop-filter:blur(16px) CSS, so we must neutralise every ancestor up
    // to (and including) that .block wrapper, then re-attach #tour-root
    // directly to <body> so all its fixed children work normally.
    // Shared helper: strip stacking-context properties from all ancestors up to
    // (and including) the nearest .block/.form, then move the element to body
    // and collapse the now-empty wrapper so it occupies zero layout space.
    function escapeToBody(elId, insertBefore) {
        var el = document.getElementById(elId);
        if (!el) return;
        var ancestor = el.parentElement;
        var blockWrapper = null;
        while (ancestor && ancestor !== document.body) {
            ancestor.style.setProperty('backdrop-filter',         'none', 'important');
            ancestor.style.setProperty('-webkit-backdrop-filter', 'none', 'important');
            ancestor.style.setProperty('background',              'transparent', 'important');
            ancestor.style.setProperty('border',                  'none', 'important');
            ancestor.style.setProperty('box-shadow',              'none', 'important');
            ancestor.style.setProperty('animation',               'none', 'important');
            ancestor.style.setProperty('padding',                 '0', 'important');
            ancestor.style.setProperty('margin',                  '0', 'important');
            var isBlock = ancestor.classList.contains('block') || ancestor.classList.contains('form');
            if (isBlock) blockWrapper = ancestor;
            ancestor = ancestor.parentElement;
            if (isBlock) break;
        }
        if (insertBefore) {
            document.body.insertBefore(el, document.body.firstChild);
        } else {
            document.body.appendChild(el);
        }
        // Collapse the orphaned empty wrapper so it occupies zero layout space.
        // Without this, Gradio's padding on .block creates an invisible-but-tall
        // strip that shifts content and partially covers fixed-position visuals.
        if (blockWrapper) {
            blockWrapper.style.setProperty('height',     '0', 'important');
            blockWrapper.style.setProperty('min-height', '0', 'important');
            blockWrapper.style.setProperty('overflow',   'hidden', 'important');
            blockWrapper.style.setProperty('display',    'block', 'important');
        }
    }

    escapeToBody('tour-root',     false);
    escapeToBody('ambient-layer', true);
    escapeToBody('bg-decor',      false);
    escapeToBody('shield-anim',   false);
    escapeToBody('bg-shields',    true);

    // ── Direct element style manipulation (handles remaining edge cases) ──
    function applyDynamicStyles() {
        // Hero header — transparent panel
        var heroId = document.getElementById('hero-header');
        if (heroId) {
            var heroTargets = [heroId];
            var inner = heroId.querySelector('.block') || heroId.querySelector('.wrap');
            if (inner) heroTargets.push(inner);
            heroTargets.forEach(function(el) {
                el.style.setProperty('background', 'transparent', 'important');
                el.style.setProperty('border', 'none', 'important');
                el.style.setProperty('box-shadow', 'none', 'important');
                el.style.setProperty('backdrop-filter', 'none', 'important');
                el.style.setProperty('-webkit-backdrop-filter', 'none', 'important');
            });
            // Hero h1 — shield icons on both sides + gradient text span
            var h1 = heroId.querySelector('h1');
            if (h1 && !h1.dataset.styled) {
                h1.dataset.styled = '1';
                var shSVG =
                    '<svg width="26" height="30" viewBox="-20 -23 40 47" xmlns="http://www.w3.org/2000/svg"' +
                    ' style="display:block;flex-shrink:0;filter:drop-shadow(0 0 5px rgba(56,232,255,0.70));">' +
                    '<path d="M0-22 L17-15 L17-4 C17 9 9 14 0 17 C-9 14-17 9-17-4 L-17-15 Z"' +
                    ' fill="rgba(10,20,55,0.95)" stroke="rgba(56,232,255,0.90)" stroke-width="1.4"/>' +
                    '<path d="M0-18 L13-12 L13-2 C13 6 7 10 0 13 C-7 10-13 6-13-2 L-13-12 Z"' +
                    ' fill="none" stroke="rgba(56,232,255,0.28)" stroke-width="0.7"/>' +
                    '<ellipse cx="0" cy="-2" rx="11" ry="3.5" fill="none"' +
                    ' stroke="rgba(56,232,255,0.28)" stroke-width="0.6" stroke-dasharray="4 4"/>' +
                    '<circle cx="0" cy="-2" r="8" fill="rgba(3,6,26,0.90)"' +
                    ' stroke="rgba(56,232,255,0.75)" stroke-width="1.1"/>' +
                    '<circle cx="0" cy="-2" r="5" fill="rgba(100,28,158,0.65)"' +
                    ' stroke="rgba(139,92,246,0.60)" stroke-width="0.8"/>' +
                    '<circle cx="0" cy="-2" r="2.5" fill="#38E8FF" opacity="0.95"/>' +
                    '<circle cx="-1.2" cy="-3.2" r="0.9" fill="rgba(255,255,255,0.88)"/>' +
                    '</svg>';
                var origText = h1.textContent.trim();
                var txtSpan =
                    '<span style="background:linear-gradient(90deg,#38E8FF 0%,#A78BFA 40%,#6EE7FF 65%,#A78BFA 100%);' +
                    '-webkit-background-clip:text;-webkit-text-fill-color:transparent;' +
                    'background-clip:text;background-size:200% auto;' +
                    'font-size:1.65rem;line-height:1.35;font-weight:700;' +
                    'font-family:Inter,system-ui,sans-serif;letter-spacing:0.02em;' +
                    'animation:heroShimmer 7s ease-in-out infinite alternate;">' +
                    origText + '</span>';
                h1.style.cssText =
                    'display:flex;align-items:center;gap:10px;margin-bottom:0.4rem;' +
                    'filter:drop-shadow(0 0 18px rgba(56,232,255,0.28));flex-wrap:wrap;';
                h1.innerHTML = shSVG + txtSpan + shSVG;
            }
            // Hero subtitle
            var pEl = heroId.querySelector('p');
            if (pEl) {
                pEl.style.setProperty('color', '#6E8CAA', 'important');
                pEl.style.setProperty('font-size', '0.88rem', 'important');
            }
        }

        // Label pills — ensure inline-flex and pill appearance
        document.querySelectorAll('.block .label-wrap, .form .label-wrap').forEach(function(el) {
            if (el.dataset.pillStyled) return;
            el.dataset.pillStyled = '1';
            el.style.setProperty('display', 'inline-flex', 'important');
            el.style.setProperty('align-items', 'center', 'important');
            el.style.setProperty('background', 'rgba(56,232,255,0.07)', 'important');
            el.style.setProperty('border', '1px solid rgba(56,232,255,0.42)', 'important');
            el.style.setProperty('border-radius', '20px', 'important');
            el.style.setProperty('padding', '3px 12px', 'important');
            el.style.setProperty('margin-bottom', '10px', 'important');
            el.style.setProperty('width', 'auto', 'important');
            el.style.setProperty('max-width', 'max-content', 'important');
            // Style the text inside
            el.querySelectorAll('span, label, label span').forEach(function(t) {
                t.style.setProperty('color', '#38E8FF', 'important');
                t.style.setProperty('-webkit-text-fill-color', '#38E8FF', 'important');
                t.style.setProperty('font-size', '0.72rem', 'important');
                t.style.setProperty('font-weight', '700', 'important');
                t.style.setProperty('letter-spacing', '0.09em', 'important');
                t.style.setProperty('text-transform', 'uppercase', 'important');
                t.style.setProperty('background', 'none', 'important');
                t.style.setProperty('-webkit-background-clip', 'unset', 'important');
            });
        });
    }

    // Run once immediately and watch for future DOM changes
    applyDynamicStyles();
    var domObserver = new MutationObserver(function() { applyDynamicStyles(); });
    domObserver.observe(document.body, { childList: true, subtree: true });

    // ── Page navigation ───────────────────────────────────────────────────────
    window.showPage = function(page) {
        var main     = document.getElementById("page-main");
        var about    = document.getElementById("page-about");
        var navHome  = document.getElementById("nav-home");
        var navAbout = document.getElementById("nav-about");
        if (!main || !about || !navHome || !navAbout) return;

        if (page === "main") {
            main.classList.add("imageshield-visible");
            main.classList.remove("imageshield-hidden");
            about.classList.add("imageshield-hidden");
            about.classList.remove("imageshield-visible");
            navHome.style.borderBottomColor  = "#38E8FF";
            navHome.style.color              = "#38E8FF";
            navHome.style.textShadow         = "0 0 10px rgba(56,232,255,0.55)";
            navAbout.style.borderBottomColor = "transparent";
            navAbout.style.color             = "#C4D4E4";
            navAbout.style.textShadow        = "none";
            var btn = gid("tour-reopen");
            if (btn) btn.style.display = "block"; // always visible on Home (hidden during active tour by tourStart)
        } else {
            main.classList.add("imageshield-hidden");
            main.classList.remove("imageshield-visible");
            about.classList.add("imageshield-visible");
            about.classList.remove("imageshield-hidden");
            navAbout.style.borderBottomColor = "#38E8FF";
            navAbout.style.color             = "#38E8FF";
            navAbout.style.textShadow        = "0 0 10px rgba(56,232,255,0.55)";
            navHome.style.borderBottomColor  = "transparent";
            navHome.style.color              = "#C4D4E4";
            navHome.style.textShadow         = "none";
            window.tourFinish && window.tourFinish(false);
            var btn = gid("tour-reopen");
            if (btn) btn.style.display = "none";
        }
    };

    var navH = document.getElementById("nav-home");
    if (navH) {
        navH.style.borderBottomColor = "#38E8FF";
        navH.style.color             = "#38E8FF";
        navH.style.textShadow        = "0 0 10px rgba(56,232,255,0.55)";
    }
    window.showPage("main");

    // ── Spotlight tour ────────────────────────────────────────────────────────
    var STEPS = [
        { title: "Welcome to SafeShot!",
          text: "SafeShot protects your personal images from AI image generation and deepfake misuse. Click Next to tour every feature.",
          targetId: null, pad: 0 },
        { title: "Step 1 — Upload Your Image",
          text: "Click or drag-and-drop to upload. Supported: JPG, PNG, WEBP.",
          targetId: "input_image", pad: 10 },
        { title: "Step 2 — Protect Your Image",
          text: "Once your image is loaded, click Protect Image to run the protection layer.",
          targetId: "protect_btn", pad: 8 },
        { title: "Step 3 — View Your Result",
          text: "Your protected image appears here.",
          targetId: "output_image", pad: 10 },
        { title: "Step 4 — Download",
          text: "Download the protected PNG. This button appears after processing completes.",
          targetId: "download_section", pad: 10 }
    ];

    var currentStep = 0, tourFinished = false;
    function gid(id) { return document.getElementById(id); }

    function positionCard(targetId, pad) {
        var card = gid("tour-card"), svg = gid("tour-svg"), hole = gid("tour-hole");
        var vw = window.innerWidth, vh = window.innerHeight, MARGIN = 20;

        // Use the actual navbar element to get its bottom edge in the viewport.
        // Falls back to 80px which safely clears the ~60px navbar + spacing.
        var navEl = document.getElementById('main-nav');
        var NAV_BOTTOM = navEl ? Math.round(navEl.getBoundingClientRect().bottom) + 16 : 80;
        NAV_BOTTOM = Math.max(NAV_BOTTOM, 80); // safety floor

        if (!targetId) {
            svg.style.display = "none";
            hole.setAttribute("width", 0); hole.setAttribute("height", 0);
            card.style.top = "50%"; card.style.left = "50%";
            card.style.transform = "translate(-50%,-50%)"; return;
        }
        var target = document.getElementById(targetId);
        if (!target) return;
        card.style.transform = "";
        var r = target.getBoundingClientRect();
        var cw = Math.min(320, vw * 0.9), ch = 230; // ch slightly larger to avoid underestimate

        hole.setAttribute("x", r.left - pad);
        hole.setAttribute("y", r.top - pad);
        hole.setAttribute("width", r.width + pad * 2);
        hole.setAttribute("height", r.height + pad * 2);
        svg.style.display = "block";

        var fits = {
            below: r.bottom + MARGIN + ch <= vh,
            above: r.top - MARGIN - ch >= NAV_BOTTOM, // must clear navbar, not just top of viewport
            right: r.right + MARGIN + cw <= vw,
            left:  r.left  - MARGIN - cw >= 0
        };
        var top, left;
        if      (fits.below) { top = r.bottom + MARGIN; left = Math.max(MARGIN, Math.min(r.left, vw - cw - MARGIN)); }
        else if (fits.above) { top = r.top - MARGIN - ch; left = Math.max(MARGIN, Math.min(r.left, vw - cw - MARGIN)); }
        else if (fits.right) { left = r.right + MARGIN; top = Math.max(NAV_BOTTOM, Math.min(r.top, vh - ch - MARGIN)); }
        else                 { left = Math.max(MARGIN, r.left - MARGIN - cw); top = Math.max(NAV_BOTTOM, Math.min(r.top, vh - ch - MARGIN)); }

        // Final safety clamp — card must never start above the navbar
        top = Math.max(NAV_BOTTOM, top);

        card.style.top  = top  + "px";
        card.style.left = left + "px";
    }

    function renderStep() {
        var s = STEPS[currentStep], total = STEPS.length;
        gid("tour-counter").textContent = (currentStep + 1) + " of " + total;
        gid("tour-title").textContent   = s.title;
        gid("tour-text").textContent    = s.text;
        gid("btn-back").style.display   = currentStep === 0           ? "none" : "";
        gid("btn-next").style.display   = currentStep === total - 1   ? "none" : "";
        gid("btn-finish").style.display = currentStep === total - 1   ? ""     : "none";
        setTimeout(function() { positionCard(s.targetId, s.pad); }, 60);
    }

    window.tourStart = function() {
        currentStep = 0; tourFinished = false;
        gid("tour-blocker").style.display = "block";
        gid("tour-card").style.display    = "block";
        gid("tour-reopen").style.display  = "none";
        renderStep();
    };
    window.tourNext   = function() { if (currentStep < STEPS.length - 1) { currentStep++; renderStep(); } };
    window.tourBack   = function() { if (currentStep > 0) { currentStep--; renderStep(); } };
    window.tourFinish = function(showButton) {
        var show = showButton !== false;
        gid("tour-svg").style.display     = "none";
        gid("tour-blocker").style.display = "none";
        gid("tour-card").style.display    = "none";
        if (show) { tourFinished = true; gid("tour-reopen").style.display = "block"; }
    };

    window.addEventListener("scroll", function() {
        var s = STEPS[currentStep];
        if (gid("tour-card").style.display !== "none") positionCard(s.targetId, s.pad);
    }, true);
    window.addEventListener("resize", function() {
        var s = STEPS[currentStep];
        if (gid("tour-card").style.display !== "none") positionCard(s.targetId, s.pad);
    });

    window.tourStart();

    // ── Download button two-line label ────────────────────────────────────────
    (function () {
        function patchBtn() {
            var section = document.getElementById("download_section");
            if (!section) return;
            var btn = (section.tagName === "A" || section.tagName === "BUTTON")
                      ? section
                      : (section.querySelector("a") || section.querySelector("button"));
            if (!btn || btn.querySelector(".dl-header")) return;
            var kids = Array.from(btn.childNodes);
            if (!kids.length) return;
            var fileSpan = document.createElement("span");
            fileSpan.style.cssText = "font-size:0.82em;opacity:0.85;display:block;";
            kids.forEach(function(n) { fileSpan.appendChild(n); });
            btn.appendChild(fileSpan);
            var header = document.createElement("span");
            header.className = "dl-header";
            header.style.cssText = "font-weight:700;font-size:1.1em;display:block;";
            header.textContent = "Download";
            btn.insertBefore(header, btn.firstChild);
            btn.style.setProperty("display",        "flex",      "important");
            btn.style.setProperty("flex-direction", "column",    "important");
            btn.style.setProperty("align-items",    "center",    "important");
            btn.style.setProperty("gap",            "3px",       "important");
            btn.style.setProperty("height",         "auto",      "important");
            btn.style.setProperty("padding",        "10px 20px", "important");
        }
        patchBtn();
        var busy = false;
        new MutationObserver(function() {
            if (busy) return; busy = true; patchBtn(); busy = false;
        }).observe(document.body, { childList: true, subtree: true, characterData: true });
    })();

    // ── MOTION DESIGN ────────────────────────────────────────────────────────

    // 1. Staggered card entrance — delay added after Gradio finishes rendering
    setTimeout(function() {
        var cards = document.querySelectorAll('#page-main .block, #page-main .form');
        cards.forEach(function(el, i) {
            if (!el.style.animationDelay) {
                el.style.animationDelay = (0.07 * i + 0.06) + 's';
            }
        });
    }, 120);

    // 2. Upload / output corner L-bracket markers
    (function addCorners() {
        function inject() {
            ['input_image', 'output_image'].forEach(function(id) {
                var blk = document.getElementById(id);
                if (!blk || blk.dataset.uc) return;
                var wrap = blk.querySelector('[data-testid="image"]');
                if (!wrap) return;
                blk.dataset.uc = '1';
                if (getComputedStyle(wrap).position === 'static') wrap.style.position = 'relative';
                ['tl','tr','bl','br'].forEach(function(c) {
                    var d = document.createElement('div');
                    d.className = 'uc ' + c;
                    wrap.appendChild(d);
                });
            });
        }
        inject();
        new MutationObserver(function() { inject(); })
            .observe(document.body, { childList: true, subtree: true });
    })();

    // 3. AI scan line — toggle .is-protecting while Gradio is busy
    (function watchProgress() {
        var col = document.getElementById('page-main');
        new MutationObserver(function() {
            var busy = !!document.querySelector(
                '[data-testid="progress-bar"], .progress, .eta-bar, .generating');
            if (col) col.classList.toggle('is-protecting', busy);
        }).observe(document.body, {
            subtree: true, childList: true,
            attributes: true, attributeFilter: ['class', 'style']
        });
    })();

    // 4. Floating ambient particles — tiny glowing dots that drift upward
    (function spawnParticles() {
        var rises  = ['pRise0','pRise1','pRise2','pRise3'];
        var colors = ['rgba(56,232,255,','rgba(124,58,237,','rgba(167,139,250,'];
        for (var i = 0; i < 16; i++) {
            var p    = document.createElement('div');
            var size = (Math.random() * 2.8 + 1).toFixed(1);
            var col  = colors[i % colors.length];
            var left = (Math.random() * 94 + 3).toFixed(1);
            var dur  = (Math.random() * 18 + 18).toFixed(1);
            var del  = (Math.random() * 22).toFixed(1);
            var glowR = (parseFloat(size) * 2.8).toFixed(1);
            var rise = rises[i % rises.length];
            p.style.cssText =
                'position:fixed;bottom:-6px;left:' + left + '%;' +
                'width:' + size + 'px;height:' + size + 'px;border-radius:50%;' +
                'background:' + col + '0.85);' +
                'box-shadow:0 0 ' + glowR + 'px ' + col + '0.55);' +
                'pointer-events:none;z-index:1;' +
                'animation:' + rise + ' ' + dur + 's ' + del + 's linear infinite;';
            document.body.appendChild(p);
        }
    })();

    // 5. Button click ripple — white burst on mousedown
    (function buttonRipple() {
        document.addEventListener('mousedown', function(e) {
            var btn = e.target.closest(
                'button.primary,button.stop,button.cancel,' +
                '#protect_btn button,#stop_btn button');
            if (!btn) return;
            var r   = btn.getBoundingClientRect();
            var rpl = document.createElement('span');
            rpl.style.cssText =
                'position:absolute;border-radius:50%;' +
                'width:8px;height:8px;margin-top:-4px;margin-left:-4px;' +
                'background:rgba(255,255,255,0.32);pointer-events:none;z-index:9999;' +
                'left:' + (e.clientX - r.left) + 'px;' +
                'top:'  + (e.clientY - r.top)  + 'px;' +
                'animation:rippleOut 0.55s ease-out forwards;';
            if (getComputedStyle(btn).position === 'static')
                btn.style.setProperty('position','relative','important');
            btn.style.overflow = 'hidden';
            btn.appendChild(rpl);
            setTimeout(function(){ rpl.remove(); }, 600);
        });
    })();

    // 6. AI shield — pulsing SVG badge injected into the output image panel
    (function injectShield() {
        function add() {
            var outBlk = document.getElementById('output_image');
            if (!outBlk || outBlk.dataset.sv) return;
            var wrap = outBlk.querySelector('[data-testid="image"]');
            if (!wrap) return;
            outBlk.dataset.sv = '1';
            if (getComputedStyle(wrap).position === 'static') wrap.style.position = 'relative';
            var sh = document.createElement('div');
            sh.id = 'shield-viz';
            sh.innerHTML =
                '<svg width="48" height="56" viewBox="0 0 22 26" fill="none">' +
                '<path d="M11 1L1 5v8c0 5.5 4.3 10.7 10 12 5.7-1.3 10-6.5 10-12V5L11 1z"' +
                ' stroke="url(#svG)" stroke-width="1.2" fill="rgba(56,232,255,0.04)"/>' +
                '<defs><linearGradient id="svG" x1="0" y1="0" x2="1" y2="1">' +
                '<stop stop-color="#38E8FF"/><stop offset="1" stop-color="#7C3AED"/>' +
                '</linearGradient></defs></svg>';
            sh.style.cssText =
                'position:absolute;bottom:14px;right:14px;pointer-events:none;z-index:4;' +
                'animation:shieldIdlePulse 3.5s ease-in-out infinite;';
            wrap.appendChild(sh);
        }
        add();
        new MutationObserver(function() { add(); }).observe(document.body, {childList:true, subtree:true});
    })();
}
"""

# ---------------------------------------------------------------------------
# Gradio layout
# ---------------------------------------------------------------------------
CUSTOM_CSS = _build_css()

with gr.Blocks() as demo:
    gr.HTML(NAV_HTML)
    gr.HTML(TOUR_HTML)
    original_image_state = gr.State(value=None)

    # ── Main page ─────────────────────────────────────────────────────────────
    with gr.Column(elem_id="page-main"):
        gr.Markdown(
            """
            # SafeShot: A Tool to Protect Personal Images

            Upload an image and obtain a protected version of it to resist Image-Generation diffusion models.
            """,
            elem_id="hero-header",
        )
        with gr.Row():
            with gr.Column(scale=6):
                input_image = gr.Image(type="pil", label="Upload Your Image",
                                       elem_id="input_image")
                resolution = gr.Radio(
                    choices=[128, 256, 512],
                    value=256,
                    label="Output Resolution",
                    info="Lower resolutions process faster.",
                )
                pgd_eps = gr.Slider(
                    minimum=4 / 255,
                    maximum=0.05,
                    value=4 / 255,
                    step=0.001,
                    label="Protection Strength",
                    info="Lower values preserve image quality; higher values improve robustness.",
                )
                steps = gr.Slider(
                    minimum=20,
                    maximum=100,
                    value=20,
                    step=10,
                    label="Optimization Steps",
                    info="More steps may strengthen protection but take longer.",
                )
                with gr.Row():
                    protect_btn = gr.Button(
                        "Protect Image",
                        variant="primary",
                        elem_id="protect_btn",
                    )
                    stop_btn = gr.Button(
                        "Stop",
                        variant="stop",
                        elem_id="stop_btn",
                    )
                text_output = gr.Textbox(label="Warning: GPU Information", visible=False,
                                         elem_id="TxtGPU")

            with gr.Column(scale=5):
                output_image = gr.Image(type="pil", label="Protected Image",
                                        elem_id="output_image")
                output_file = gr.DownloadButton(
                    label="Download Protected Image", variant="primary",
                    visible=False, elem_id="download_section",
                    elem_classes="download_section",
                )

        input_image.upload(
            fn=store_original_image,
            inputs=[input_image, resolution],
            outputs=[original_image_state, input_image],
        )
        input_image.clear(
            fn=lambda: (None, None),
            outputs=[original_image_state, input_image],
        )
        resolution.change(
            fn=refresh_input_preview,
            inputs=[original_image_state, resolution],
            outputs=input_image,
        )

        # Event wiring
        prerequisite_event = protect_btn.click(
            fn=prereq_gpu,
            inputs=original_image_state,
            outputs=text_output,
        )
        protection_event = prerequisite_event.success(
            fn=model,
            inputs=[original_image_state, resolution, pgd_eps, steps],
            outputs=[output_image, output_file],
        )
        stop_btn.click(
            fn=stop_protection,
            outputs=text_output,
            cancels=[protection_event],
            queue=False,
        )

    # ── About page ────────────────────────────────────────────────────────────
    with gr.Column(elem_id="page-about"):
        gr.Markdown(
            """
            # About This Tool

            ---

            ## Project context

            With the increase of capacity in AI models, many cases of misusage have been reported,
            one of which is the generation of harmful images, known as deepfakes, specifically with diffusion models
            such as Stable Diffusion or DALL·E.

            As part of the AI4Good Lab, our team wants to create a project to mitigate this issue, by trying to prevent these
            generations in the first place. Our team gathered resources on current available models that can add a protection layer
            on top of your original personal image-so that diffusion models wouldn't be able to edit it when prompted-and we
            came up with a user-friendly product for everyone to use.

            ---

            ## What does it do?

            Using adversarial pertubation, our tool will add a protection layer that consists of pixel-level noise, computed just enough
            so that the change is small enough to remain undetected with the human eye, but big enough to disrupt an Image-Generation process by a
            diffusion model. You can then download the protected version of your image.

            The goal is to confuse the AI when it's following a malicious prompt. If anyone now tries to feed your protected image into an AI diffusion model
            in order to edit it, the output result would look unrealistic, defeating the malicious intent.

            **<u>IMPORTANT:</u>** We can't promise universal protection. Our project goal is to raise the cost of
            malicious image editing, and offer a mitigating solution for everyone to use.

            ---

            ## How does it work?

            Our tool is heavily built upon already researched models:
            - **Photoguard** - One of the earliest proposed baseline model, given a target noise image (i.e. a complete gray image),
            it adds pertubations to mislead the AI model when trying to see the image's inner representation. The output result tends to resemble the
            noise image.
            - **EditShield** - The model acts as a more robust version of the baseline model of PhotoGuard, trained against instruction-based image editing.
            - **BlurGuard** - BlurGuard is a more recent model that adds a robust layer on top of a baseline protection layer. Given a pixel-level
            protection, it will segment the image, and apply blurring on top of the noise such that the protection layer can't easily be reversed by an attacker.

            **<u>IMPORTANT:</u>** We didn't use any explicit or harmful content when running experiments and demos on our tool.

            ---

            ## Evaluation metrics

            We chose to aim our evaluations at specific types of protection,
            - **FaceSwap** - We run evaluations against Roop, an AI model available on Huggingface that tries to faceswap two different
            identities given an orignal image and a target image.

            - **Instruction-based editing** - We test our model against Stable Diffusion, with specific instruction prompts.

            ---

            """
        )
        gr.HTML(
            """
            <div style="margin-top:8px;">
              <a onclick="window.showPage('main')"
                 style="cursor:pointer;display:inline-flex;align-items:center;gap:6px;
                        padding:11px 26px;
                        background:linear-gradient(135deg,#00D9FF,#7C3AED);
                        color:#040E1C;border-radius:10px;
                        font-weight:700;font-size:14px;text-decoration:none;
                        box-shadow:0 0 18px rgba(56,232,255,0.34),0 4px 14px rgba(0,0,0,0.3);
                        letter-spacing:0.03em;font-family:'Inter',system-ui,sans-serif;"
                 onmouseover="this.style.filter='brightness(1.1)';this.style.transform='translateY(-1px)';"
                 onmouseout="this.style.filter='none';this.style.transform='none';">
                &larr; Back to the Tool
              </a>
            </div>
            """
        )

    demo.load(fn=None, js=ALL_JS)


def launch() -> None:
    cleanup_old_outputs()
    open_browser = os.environ.get("IMAGESHIELD_OPEN_BROWSER", "1") != "0"
    demo.queue()
    demo.launch(
        server_name="127.0.0.1",
        inbrowser=open_browser,
        share=False,
        theme=gr.themes.Base(
            primary_hue=gr.themes.colors.cyan,
            secondary_hue=gr.themes.colors.purple,
            neutral_hue=gr.themes.colors.slate,
            font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
        ),
        css=_build_css(),
        allowed_paths=[str(OUTPUT_DIR), str(BG_IMAGE_PATH.parent)],
    )


if __name__ == "__main__":
    launch()
