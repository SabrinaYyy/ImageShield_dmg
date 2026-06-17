"""
Design User Interface (Web-based)
1. The model (baseline of either EditShield or PhotoGuard) has input of an image, and an output of a protected version of the image.
2. The web-based interface should be made user friendly, such that anyone is able to use it easily (it should not involve
any code running inside the terminal)
"""

# Import necessary packages
import os
import time
import uuid
from pathlib import Path

import gradio as gr
from PIL import Image, ImageOps

from .protection import (
    ProtectionCancelled,
    ProtectionService,
    ProtectionSettings,
    device_summary,
)
from .resources import user_data_dir

SERVICE = ProtectionService()
OUTPUT_DIR = user_data_dir() / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MAX_OUTPUT_AGE_SECONDS = 24 * 60 * 60


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
    """
    Before running the model, detect whether or not the current PC has a GPU to see if the computations can be done successfully.
    Supports NVIDIA GPUs (Windows/Linux) and Apple Silicon MPS (macOS).
    """
    if image is None:
        raise gr.Error("Please upload an image first.")
    status = f"Processing device: {device_summary(SERVICE.device)}"
    return gr.update(value=status, visible=True)


def model(original_image, resolution, pgd_eps, steps, progress=gr.Progress()):
    """
    The function is the root of the model function. The model acts as the image protector, given an image as an input, it will return the protected version
    of the image as an output. 
    """
    if original_image is None:
        raise gr.Error("Please upload an image first.")

    square_input = square_crop_image(original_image, resolution)
    settings = ProtectionSettings(
        resolution=int(resolution),
        eps=float(pgd_eps),
        steps=int(steps),
    )

    try:
        progress(0, desc="Loading the offline protection model")
        protected_image = SERVICE.protect(
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
    image_file_name = Path(output_path).name
    # Make the download button (and temp file) visible after protect image generation
    return protected_image, gr.update(
        label=image_file_name,
        value=str(output_path),
        visible=True,
    )


def stop_protection():
    SERVICE.cancel()
    return gr.update(
        value="Stopping protection after the current optimization step...",
        visible=True,
    )

# ---------------------------------------------------------------------------
# Navigation bar — "About" link sits on the right
# ---------------------------------------------------------------------------
# Create HTML code for the top bar
# Top left is the Web-Dev Name "Image Protection tool" with given sizing and fonts
# Top right is the two pages on our Web-Dev, link to the Home page and link to the About page with given sizing and fonts
NAV_HTML = """
<!-- This is for the tool title, create a horizontal bar with two sides, tool title and navigation links -->
<div style="display:flex; justify-content:space-between; align-items:center;
            padding:12px 4px; border-bottom:2px solid #e5e7eb; margin-bottom:8px;">
  <span style="font-size:15px; font-weight:700; color:#1e40af; letter-spacing:.01em;">
    ImageShield Tool
  </span>
<!-- This is for both the Home (page link) and the About (page link), each are linked with a function so that it shows the correct page
when clicking upon either of them (in-line click) -->
  <div style="display:flex; gap:24px;">
    <a onclick="window.showPage('main')"
       style="cursor:pointer; font-size:14px; font-weight:600; color:#374151;
              text-decoration:none; padding:4px 0; border-bottom:2px solid transparent;"
       id="nav-home">Home</a>
    <a onclick="window.showPage('about')"
       style="cursor:pointer; font-size:14px; font-weight:600; color:#374151;
              text-decoration:none; padding:4px 0; border-bottom:2px solid transparent;"
       id="nav-about">About</a>
  </div>
</div>
"""

# ---------------------------------------------------------------------------
# Spotlight tour overlay — HTML skeleton only (Gradio strips <script> tags)
# ---------------------------------------------------------------------------
# Create HTML code for the tour of the website

TOUR_HTML = """
<div id="tour-root">
<! -- Full-screen dark overlay with a transparent "hole" cut out to spotlight a UI element 
A white rectangle covers the whole screen, and the black tour-hole punches a transparent cutout — 
where it's black in the mask, the dark overlay becomes see-through.
-->
  <svg id="tour-svg"
       style="display:none; position:fixed; top:0; left:0;
              width:100vw; height:100vh; z-index:10000; pointer-events:none;">
    <defs>
    <! -- Create a mask of the spotlight widget -->
      <mask id="tour-mask">
        <rect width="100%" height="100%" fill="white"/>
        <rect id="tour-hole" rx="10" ry="10" fill="black"/>
      </mask>
    </defs>
    <rect width="100%" height="100%" fill="rgba(0,0,0,0.68)" mask="url(#tour-mask)"/>
  </svg>

  <! -- Block the clicks of any other buttons on the website when inside the tour -->
  <div id="tour-blocker"
       style="display:none; position:fixed; top:0; left:0;
              width:100%; height:100%; z-index:9999;"></div>

<! -- The popup card showing the step title, description, and Back/Next/Finish buttons -->
  <div id="tour-card"
       style="display:none; position:fixed; z-index:10001;
              background:white; border-radius:14px; padding:24px;
              max-width:320px; width:min(320px,90vw);
              box-shadow:0 8px 32px rgba(0,0,0,0.28);
              font-family:system-ui,sans-serif;">
    <div style="display:flex; justify-content:space-between;
                align-items:center; margin-bottom:10px;">
      <span id="tour-counter"
            style="font-size:11px; font-weight:700; letter-spacing:.06em;
                   color:#6b7280; text-transform:uppercase;"></span>
      <button onclick="window.tourFinish()"
              style="background:none; border:none; font-size:22px;
                     cursor:pointer; color:#9ca3af; line-height:1; padding:0;">
        &times;</button>
    </div>
    <h3 id="tour-title"
        style="margin:0 0 8px; font-size:17px; font-weight:700; color:#111827;"></h3>
    <p id="tour-text"
       style="margin:0 0 20px; font-size:14px; line-height:1.65; color:#4b5563;"></p>
    <div style="display:flex; gap:8px; justify-content:flex-end;">
      <button id="btn-back" onclick="window.tourBack()"
              style="padding:9px 18px; border-radius:8px; border:1px solid #d1d5db;
                     background:white; cursor:pointer; font-size:13px;
                     font-weight:600; color:#374151;">Back</button>
      <button id="btn-next" onclick="window.tourNext()"
              style="padding:9px 20px; border-radius:8px; border:none;
                     background:#2563eb; color:white; cursor:pointer;
                     font-size:13px; font-weight:600;">Next</button>
      <button id="btn-finish" onclick="window.tourFinish()"
              style="display:none; padding:9px 20px; border-radius:8px; border:none;
                     background:#16a34a; color:white; cursor:pointer;
                     font-size:13px; font-weight:600;">Finish Tour</button>
    </div>
  </div>

  <! -- Fixed "Take the Tour" button, on the right bottom of the screen, that reappears after the tour is finished -->
  <button id="tour-reopen" onclick="window.tourStart()"
          style="display:none; position:fixed; bottom:24px; right:24px;
                 z-index:9998; background:#2563eb; color:white; border:none;
                 border-radius:50px; padding:11px 20px; font-size:13px;
                 font-weight:700; cursor:pointer;
                 box-shadow:0 4px 14px rgba(37,99,235,.45);">
    ? Take the Tour
  </button>
</div>
"""

# ---------------------------------------------------------------------------
# All JavaScript — runs via demo.load() after Gradio finishes rendering
# ---------------------------------------------------------------------------
ALL_JS = """
() => {
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

    // ── Page navigation ─────────────────────────────────────────────────────
    // Toggles display: block / none on #page-main and #page-about to simulate a two-page app within a single Gradio page.
    // Updates the nav link styles (blue underline = active page).
    
    window.showPage = function(page) {
        const main     = document.getElementById("page-main");
        const about    = document.getElementById("page-about");
        const navHome  = document.getElementById("nav-home");
        const navAbout = document.getElementById("nav-about");

        // Null guards — if any element is missing, skip silently
        if (!main || !about || !navHome || !navAbout) return;

        if (page === "main") {
        // Show the Main page
            // Show the main page, dont show about page
            main.style.display  = "block";
            about.style.display = "none";
            // Define colour border for Home page
            navHome.style.borderBottomColor  = "#2563eb";
            navHome.style.color              = "#2563eb";
            // The About page is not selected, not underlines
            navAbout.style.borderBottomColor = "transparent";
            navAbout.style.color             = "#374151";
            // Only restore the reopen button if the user has already finished the tour
            const btn = gid("tour-reopen");
            if (btn && tourFinished) btn.style.display = "block";
        } else {
        // When navigating to "about", it also closes the tour and hides the reopen button.
            main.style.display  = "none";
            about.style.display = "block";
            navAbout.style.borderBottomColor = "#2563eb";
            navAbout.style.color             = "#2563eb";
            navHome.style.borderBottomColor  = "transparent";
            navHome.style.color              = "#374151";
            // Close the tour (if open) and hide the reopen button — it belongs on Home only
            window.tourFinish && window.tourFinish(false);
            const btn = gid("tour-reopen");
            if (btn) btn.style.display = "none";
        }
    };

    // Highlight Home nav link on load (Gradio already hides page-about via visible=False)
    const navHome = document.getElementById("nav-home");
    if (navHome) { navHome.style.borderBottomColor = "#2563eb"; navHome.style.color = "#2563eb"; }

    // ── Spotlight tour ───────────────────────────────────────────────────────
    const STEPS = [
    // Define all steps of the tour with their spotlight widget
        {
            title: "Welcome to the ImageShield Tool!",
            text:  "This tool is designed to protect your image from AI Image Generation Models" +
                   "Click Next to visit every feature.",
            targetId: null, pad: 0
        },
        {
            title: "Step 1 — Upload Your Image",
            text:  "Click this box or drag and drop to upload an image here. " +
                   "You can also choose other means of upload, among the three icons. " +
                   "Supported formats: JPG, PNG, WEBP.",
            targetId: "input_image", pad: 10
        },
        {
            title: "Step 2 — Protect Your Image",
            text:  "Once your image is loaded, click Protect Image to run " +
                   "the protection layer.",
            targetId: "protect_btn", pad: 8
        },
        {
            title: "Step 3 — View Your Result",
            text:  "Your protected image appears here. ",
            targetId: "output_image", pad: 10
        },
        {
            title: "Step 4 — Download Your Protected Image",
            text:  "Click the download button below to download the protected image " +
                   "as a PNG to your device. This button appears after you click Protect Image.",
            targetId: "download_section", pad: 10
        }
    ];

    // Required functions to make the tour
    let currentStep = 0;
    let tourFinished = false;
    function gid(id) { return document.getElementById(id); }

    function positionCard(targetId, pad) {
        // Get card information
        const card = gid("tour-card"), svg = gid("tour-svg"), hole = gid("tour-hole");
        // Get screen size information
        const vw = window.innerWidth, vh = window.innerHeight, MARGIN = 14;

        // Try to find the target widget
        if (!targetId) {
            svg.style.display = "none";
            hole.setAttribute("width", 0); hole.setAttribute("height", 0);
            card.style.top = "50%"; card.style.left = "50%";
            card.style.transform = "translate(-50%,-50%)";
            return;
        }

        // Find the widget and its contour to highlight it
        const target = document.getElementById(targetId);
        if (!target) return;

        card.style.transform = "";
        const r = target.getBoundingClientRect();
        const cw = Math.min(320, vw * 0.9), ch = 210;

        // Position the hole first, then show the SVG — prevents full-screen dark flash
        hole.setAttribute("x",      r.left   - pad);
        hole.setAttribute("y",      r.top    - pad);
        hole.setAttribute("width",  r.width  + pad * 2);
        hole.setAttribute("height", r.height + pad * 2);
        svg.style.display = "block";

        // Define card borders around the widget, and the text below it so describe the step
        // Find where to fit the text box that comes to describe near the actual widget
        // Should we place the tour card left, right, above, or below the current highlight widget
        const fits = {
            below: r.bottom + MARGIN + ch <= vh,
            above: r.top    - MARGIN - ch >= 0,
            right: r.right  + MARGIN + cw <= vw,
            left:  r.left   - MARGIN - cw >= 0
        };
        let top, left;
        if      (fits.below) { top = r.bottom + MARGIN; left = Math.max(MARGIN, Math.min(r.left, vw - cw - MARGIN)); }
        else if (fits.above) { top = r.top - MARGIN - ch; left = Math.max(MARGIN, Math.min(r.left, vw - cw - MARGIN)); }
        else if (fits.right) { left = r.right + MARGIN; top = Math.max(MARGIN, Math.min(r.top, vh - ch - MARGIN)); }
        else                 { left = Math.max(MARGIN, r.left - MARGIN - cw); top = Math.max(MARGIN, Math.min(r.top, vh - ch - MARGIN)); }

        card.style.top = top + "px"; card.style.left = left + "px";
    }

    // Figure out current step, with the text that comes with it, and which buttons to activate (next or finish tour and back)
    function renderStep() {
        const s = STEPS[currentStep], total = STEPS.length;
        // Display step number
        gid("tour-counter").textContent = (currentStep + 1) + " of " + total;
        // Display step name
        gid("tour-title").textContent   = s.title;
        // Display step description
        gid("tour-text").textContent    = s.text;
        // Display necessary buttons at certain step counts. Back button for all steps except first, Next button for all steps except last
        // Finish button only for last
        gid("btn-back").style.display   = currentStep === 0           ? "none" : "";
        gid("btn-next").style.display   = currentStep === total - 1   ? "none" : "";
        gid("btn-finish").style.display = currentStep === total - 1   ? ""     : "none";
        setTimeout(() => positionCard(s.targetId, s.pad), 60);
    }

    // Once tour starts, we block other buttons, only show the current cards
    window.tourStart = function() {
        // State of starting the tour
        currentStep = 0;
        tourFinished = false;
        gid("tour-blocker").style.display = "block";
        gid("tour-card").style.display    = "block";
        gid("tour-reopen").style.display  = "none";
        // SVG is shown inside positionCard after the hole is stamped — no premature dark flash
        renderStep();
    };
    // Render next step when button Next
    window.tourNext   = function() { if (currentStep < STEPS.length - 1) { currentStep++; renderStep(); } };
    // Render previous step when button Back
    window.tourBack   = function() { if (currentStep > 0) { currentStep--; renderStep(); } };
    // Finish the tour, disable the tour cards and svg
    window.tourFinish = function(showButton) {
        // showButton defaults to true; pass false when called from showPage("about")
        const show = showButton !== false;
        gid("tour-svg").style.display     = "none";
        gid("tour-blocker").style.display = "none";
        gid("tour-card").style.display    = "none";
        if (show) {
            tourFinished = true;
            gid("tour-reopen").style.display = "block";
        }
    };

    // Verify action of scrolling and resizing for the window when in tour mode
    window.addEventListener("scroll", () => {
        const s = STEPS[currentStep];
        if (gid("tour-card").style.display !== "none") positionCard(s.targetId, s.pad);
    }, true);
    window.addEventListener("resize", () => {
        const s = STEPS[currentStep];
        if (gid("tour-card").style.display !== "none") positionCard(s.targetId, s.pad);
    });

    // Start the tour immediately upon web openening
    window.tourStart();

    // ── Download button two-line label ──────────────────────────────────────
    (function () {
    // Make the download button have a multi-line label (Download on top, and image number on bottom)
        function patchBtn() {
        // Get the button element id
            var section = document.getElementById("download_section");
            if (!section) return;
            var btn = (section.tagName === "A" || section.tagName === "BUTTON")
                      ? section
                      : (section.querySelector("a") || section.querySelector("button"));
            if (!btn || btn.querySelector(".dl-header")) return;

            // Move all existing children into a small-text span WITHOUT removing
            // them from the live DOM tree — this keeps Svelte's text node reference
            // alive so future label updates still render correctly.
            // Need to create span level inside the code once the Download button appears
            var kids = Array.from(btn.childNodes);
            if (!kids.length) return;
            var fileSpan = document.createElement("span");
            fileSpan.style.cssText = "font-size:0.82em;opacity:0.85;display:block;";
            kids.forEach(function (n) { fileSpan.appendChild(n); });
            btn.appendChild(fileSpan);

            // Prepend bold "Download" header
            var header = document.createElement("span");
            header.className = "dl-header";
            header.style.cssText = "font-weight:700;font-size:1.1em;display:block;";
            header.textContent = "Download";
            btn.insertBefore(header, btn.firstChild);

            // Stack items vertically (setProperty supports !important)
            // Set visual text placement
            btn.style.setProperty("display",        "flex",    "important");
            btn.style.setProperty("flex-direction", "column",  "important");
            btn.style.setProperty("align-items",    "center",  "important");
            btn.style.setProperty("gap",            "3px",     "important");
            btn.style.setProperty("height",         "auto",    "important");
            btn.style.setProperty("padding",        "10px 20px", "important");
        }

        // Listen (observe) when the Download button is appearing
        patchBtn(); // run once immediately on page load
        var busy = false;
        new MutationObserver(function () {
            if (busy) return;
            busy = true;
            patchBtn();
            busy = false;
        // characterData catches Svelte's textNode.data = newLabel updates
        }).observe(document.body, { childList: true, subtree: true, characterData: true });
    })();
}
"""

# ---------------------------------------------------------------------------
# Gradio layout
# ---------------------------------------------------------------------------
# Hide page-about via plain CSS (no !important) so JS inline styles can override it
CUSTOM_CSS = """
#page-about {
    display: none;
}
"""

with gr.Blocks() as demo:
    # Link the HTMl files with the Gradio app demo
    gr.HTML(NAV_HTML)
    gr.HTML(TOUR_HTML)
    original_image_state = gr.State(value=None)

    # ── Main page ────────────────────────────────────────────────────────────
    with gr.Column(elem_id="page-main"):
        gr.Markdown(
            """
            # 🛡️ ImageShield: A Tool to Protect Personal Images 🛡️

            Upload an image and obtain a protected version of it to resist
            Image-Generation diffusion models.
            """
        )
        with gr.Row():
            # Create the interface on the Main Page, upload image, and protect button under same column
            with gr.Column():
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

            # Create output image and output file under same column
            with gr.Column():
                output_image = gr.Image(type="pil", label="Protected Image",
                                        elem_id="output_image")
                output_file = gr.DownloadButton(label="Download Protected Image", variant="primary",
                                      visible=False, elem_id="download_section", elem_classes="download_section")

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

        # Create function for the protect image button, run the prereq to check gpu requirements, and then run model function
        prerequisite_event = protect_btn.click(
            fn=prereq_gpu, 
            inputs=original_image_state, 
            outputs=text_output
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

    # ── About page ───────────────────────────────────────────────────────────
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
                 style="cursor:pointer; display:inline-block; padding:10px 22px;
                        background:#2563eb; color:white; border-radius:8px;
                        font-weight:600; font-size:14px; text-decoration:none;">
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
        theme=gr.themes.Soft(),
        css=CUSTOM_CSS,
        allowed_paths=[str(OUTPUT_DIR)],
    )


if __name__ == "__main__":
    launch()
