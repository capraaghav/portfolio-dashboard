"""ClickSpark — click-burst spark animation, ported from React Bits to Streamlit.

The React original wraps children in a relative <div> with a <canvas> overlay and
sparks on click. Streamlit can't host React, so this draws a transparent, full-window
<canvas> over the whole app and sparks wherever you click.

The spark code is injected into the document that owns the app UI and runs there, so it
overlays the entire app and persists across Streamlit reruns (a guard prevents double
init; each rerun just refreshes the live config). Works whether the JS is delivered via
the modern `st.html(..., unsafe_allow_javascript=True)` (runs in the main document) or
the legacy `components.html` iframe (injects into `window.parent`) — the script picks
the right target window automatically.
"""

from __future__ import annotations
import inspect
import json
import streamlit as st

_JS = r"""
<script>
(function () {
  // Target window that owns the visible app: parent when we're in an iframe, else self.
  const W = (window.parent && window.parent !== window) ? window.parent : window;
  W.__clickSparkCfg = __CFG__;                 // live config (refreshed every rerun)
  if (W.__clickSparkInit) return;              // already installed on this document
  W.__clickSparkInit = true;

  // Stringified and appended to W.document so it runs in that document's context
  // (and therefore survives Streamlit reruns / iframe swaps).
  const code = function () {
    if (document.getElementById('__clickSparkCanvas')) return;
    const cfg = () => window.__clickSparkCfg || {};
    const canvas = document.createElement('canvas');
    canvas.id = '__clickSparkCanvas';
    Object.assign(canvas.style, {
      position: 'fixed', top: '0', left: '0', width: '100%', height: '100%',
      pointerEvents: 'none', zIndex: '2147483646'
    });
    document.body.appendChild(canvas);
    const ctx = canvas.getContext('2d');
    let sparks = [];

    const resize = () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight; };
    resize();
    window.addEventListener('resize', resize);

    const ease = (t, e) =>
      e === 'linear' ? t :
      e === 'ease-in' ? t * t :
      e === 'ease-in-out' ? (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t) :
      t * (2 - t);  // ease-out (default)

    window.addEventListener('click', (ev) => {
      const c = cfg(), now = performance.now(), n = c.sparkCount || 8;
      for (let i = 0; i < n; i++) {
        sparks.push({ x: ev.clientX, y: ev.clientY, angle: (2 * Math.PI * i) / n, startTime: now });
      }
    });

    const draw = (ts) => {
      const c = cfg();
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      sparks = sparks.filter((sp) => {
        const elapsed = ts - sp.startTime, dur = c.duration || 400;
        if (elapsed >= dur) return false;
        const eased = ease(elapsed / dur, c.easing || 'ease-out');
        const dist = eased * (c.sparkRadius || 30) * (c.extraScale || 1);
        const len = (c.sparkSize || 13) * (1 - eased);
        const x1 = sp.x + dist * Math.cos(sp.angle), y1 = sp.y + dist * Math.sin(sp.angle);
        const x2 = sp.x + (dist + len) * Math.cos(sp.angle), y2 = sp.y + (dist + len) * Math.sin(sp.angle);
        ctx.strokeStyle = c.sparkColor || '#C9A87A';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
        return true;
      });
      requestAnimationFrame(draw);
    };
    requestAnimationFrame(draw);
  };

  const s = W.document.createElement('script');
  s.textContent = '(' + code.toString() + ')();';
  W.document.body.appendChild(s);
})();
</script>
"""


def click_spark(spark_color: str = "#C9A87A", spark_size: int = 13, spark_radius: int = 30,
                spark_count: int = 9, duration: int = 400, easing: str = "ease-out",
                extra_scale: float = 1.0) -> None:
    """Enable the global click-spark effect over the whole app. Call once per run
    (e.g. right after the page CSS). Props mirror the React component."""
    cfg = json.dumps({
        "sparkColor": spark_color, "sparkSize": spark_size, "sparkRadius": spark_radius,
        "sparkCount": spark_count, "duration": duration, "easing": easing, "extraScale": extra_scale,
    })
    html = _JS.replace("__CFG__", cfg)

    # Prefer the modern st.html(unsafe_allow_javascript=…); fall back to the legacy
    # components iframe on older Streamlit.
    if hasattr(st, "html") and "unsafe_allow_javascript" in inspect.signature(st.html).parameters:
        st.html(html, unsafe_allow_javascript=True)
    else:
        import streamlit.components.v1 as components
        components.html(html, height=0)
