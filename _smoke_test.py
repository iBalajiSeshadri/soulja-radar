"""
_smoke_test.py — headless execution harness for app.py.

Stubs Streamlit so we can actually RUN app.py top-to-bottom in a chosen draft mode
and catch runtime errors (the kind that only surface when the code executes, not
just compiles). Used to verify snake mode isn't broken.

Usage: MODE=snake python3 _smoke_test.py   (or MODE=auction)
"""
import os, sys, types

MODE = os.environ.get("MODE", "snake")

# ── minimal Streamlit stub ────────────────────────────────────────────────────
class _Ctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __getattr__(self, name):
        def _f(*a, **k):
            return _widget_return(name, a, k)
        return _f

class _Sidebar:
    def __getattr__(self, name):
        def _f(*a, **k):
            return _widget_return(name, a, k)
        return _f
    def expander(self, *a, **k): return _Ctx()

_radio_answers = {
    "Draft Format:": "🐍 Snake Draft" if MODE == "snake" else "🔨 Auction / Salary Cap",
    "QB Roster Format:": "⚡ Superflex / 2-QB",
    "Defensive Format:": "🛡️ Offense + IDP (Soulja)",
}

def _widget_return(name, args, kwargs):
    label = args[0] if args else kwargs.get("label", "")
    # radios
    if name == "radio":
        for k, v in _radio_answers.items():
            if isinstance(label, str) and k in label:
                return v
        opts = args[1] if len(args) > 1 else kwargs.get("options", [""])
        return opts[0] if opts else ""
    if name == "selectbox":
        opts = args[1] if len(args) > 1 else kwargs.get("options", [""])
        return opts[0] if opts else ""
    if name == "number_input":
        return kwargs.get("value", args[2] if len(args) > 2 else 10)
    if name in ("text_input",):
        return kwargs.get("value", "")
    if name in ("button", "checkbox", "toggle"):
        return False
    if name == "multiselect":
        return []
    if name == "columns":
        n = args[0] if args else 1
        n = n if isinstance(n, int) else len(n)
        return [_Ctx() for _ in range(n)]
    if name == "tabs":
        n = len(args[0]) if args else 1
        return [_Ctx() for _ in range(n)]
    if name in ("container", "expander", "form", "spinner", "status", "chat_message"):
        return _Ctx()
    if name == "metric":
        return None
    return None

class _St(types.ModuleType):
    def __init__(self):
        super().__init__("streamlit")
        self.sidebar = _Sidebar()
        self.session_state = {}
    def __getattr__(self, name):
        def _f(*a, **k):
            return _widget_return(name, a, k)
        return _f
    # session_state supports attribute + item access like the real thing
    def cache_data(self, *a, **k):
        if a and callable(a[0]):
            return a[0]
        def _wrap(fn): return fn
        return _wrap
    cache_resource = cache_data

# make session_state behave (attr + dict)
class _SS(dict):
    def __getattr__(self, k):
        try: return self[k]
        except KeyError: raise AttributeError(k)
    def __setattr__(self, k, v): self[k] = v

st = _St()
st.session_state = _SS()
sys.modules["streamlit"] = st
# stub streamlit_autorefresh
sa = types.ModuleType("streamlit_autorefresh")
sa.st_autorefresh = lambda *a, **k: 0
sys.modules["streamlit_autorefresh"] = sa

print(f"=== Executing app.py in MODE={MODE} ===")
try:
    with open("app.py") as f:
        code = f.read()
    exec(compile(code, "app.py", "exec"), {"__name__": "__main__"})
    print(f"✅ app.py ran to completion in {MODE} mode — NO runtime errors.")
except SystemExit:
    print("✅ app.py hit st.stop()/SystemExit (benign) — no crash.")
except Exception as e:
    import traceback
    print(f"❌ RUNTIME ERROR in {MODE} mode:")
    traceback.print_exc()
    sys.exit(1)
