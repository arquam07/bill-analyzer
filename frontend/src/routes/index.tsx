import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect, useRef } from "react";
import { useAuth } from "~/auth/AuthContext";
import "~/landing.css";

const ITEMS = [
  { nm: "Bulgarian Yogurt",   pr: "170.64", tax: "incl. 8%" },
  { nm: "Royal Bread",        pr: "214.92", tax: "incl. 8% · ÷2" },
  { nm: "Okutanba Eggs",      pr: "386.64", tax: "incl. 8%" },
  { nm: "Small Shopping Bag", pr: "3.30",   tax: "incl. 10% · ÷2" },
];

function InsightsMockup() {
  const bars = [65, 80, 45, 90, 55, 100, 70, 85, 60, 95, 75, 88];
  const months = ["Jun","Jul","Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar","Apr","May"];
  return (
    <div style={{ padding: "24px 22px 18px", height: "300px", display: "flex", flexDirection: "column", gap: "14px", fontFamily: "'Spline Sans Mono', monospace" }}>
      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
        <span style={{ background: "var(--green-soft)", color: "var(--green)", padding: "7px 13px", borderRadius: "8px", fontSize: "12px", fontWeight: 600 }}>¥48,320 spent</span>
        <span style={{ background: "rgba(224,83,61,0.1)", color: "var(--accent-deep)", padding: "7px 13px", borderRadius: "8px", fontSize: "12px", fontWeight: 600 }}>¥12,100 split</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: "7px" }}>
        {(["Groceries","Dining","Transport"] as const).map((cat, i) => (
          <div key={cat} style={{ background: "rgba(224,83,61,0.06)", borderRadius: "9px", padding: "9px 11px" }}>
            <div style={{ fontSize: "9px", color: "var(--ink-faint)", marginBottom: "3px" }}>{cat}</div>
            <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--ink)" }}>{["¥22,100","¥15,400","¥8,820"][i]}</div>
          </div>
        ))}
      </div>
      <div style={{ flex: 1, display: "flex", alignItems: "flex-end", gap: "4px" }}>
        {bars.map((h, i) => (
          <div key={i} style={{ flex: 1, borderRadius: "3px 3px 0 0", height: `${h}%`, background: i === 11 ? "var(--accent)" : "rgba(224,83,61,0.22)" }} />
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "9px", color: "var(--ink-faint)" }}>
        {months.map(m => <span key={m}>{m}</span>)}
      </div>
    </div>
  );
}

function LandingPage() {
  const { user, isLoading } = useAuth();
  const navigate = useNavigate();

  const scanRef = useRef<HTMLDivElement>(null);
  const splitCardRef = useRef<HTMLDivElement>(null);
  const replayRef = useRef<HTMLButtonElement>(null);
  const rowsRef = useRef<HTMLDivElement>(null);
  const receiptRef = useRef<HTMLDivElement>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const hasStartedRef = useRef(false);

  useEffect(() => {
    if (!isLoading && user) void navigate({ to: "/dashboard" });
  }, [user, isLoading, navigate]);

  const runDemo = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
    const scan = scanRef.current;
    const splitCard = splitCardRef.current;
    const replay = replayRef.current;
    const rows = rowsRef.current;
    if (!scan || !splitCard || !replay || !rows) return;

    scan.classList.remove("run");
    splitCard.classList.remove("show");
    replay.classList.remove("show");
    void scan.offsetWidth; // force reflow to restart CSS animation
    scan.classList.add("run");

    rows.innerHTML = "";
    ITEMS.forEach((item, i) => {
      const row = document.createElement("div");
      row.className = "r-row";
      row.innerHTML = `<div class="r-nm">${item.nm}<div class="r-tax">${item.tax}</div></div><div class="r-pr">¥${item.pr}</div>`;
      rows.appendChild(row);
      timersRef.current.push(setTimeout(() => row.classList.add("show"), 500 + i * 330));
    });

    const delay = 500 + ITEMS.length * 330;
    timersRef.current.push(setTimeout(() => splitCard.classList.add("show"), delay + 250));
    timersRef.current.push(setTimeout(() => replay.classList.add("show"), delay + 700));
  }, []);

  // Auto-start demo when receipt scrolls into view
  useEffect(() => {
    const receipt = receiptRef.current;
    if (!receipt) return;
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting && !hasStartedRef.current) {
          hasStartedRef.current = true;
          setTimeout(runDemo, 350);
        }
      });
    }, { threshold: 0.4 });
    obs.observe(receipt);
    return () => obs.disconnect();
  }, [runDemo]);

  // Scroll reveals
  useEffect(() => {
    const els = document.querySelectorAll(".lp .reveal");
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) { e.target.classList.add("in"); obs.unobserve(e.target); }
      });
    }, { threshold: 0.15 });
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  useEffect(() => () => timersRef.current.forEach(clearTimeout), []);

  return (
    <div className="lp">
      {/* NAV */}
      <div className="wrap">
        <nav>
          <div className="brand"><span className="mk">¥</span> Bill Analyzer</div>
          <div className="nav-links">
            <a href="#how">How it works</a>
            <a href="#why">Why it's different</a>
            <a href="#insights">Insights</a>
            <Link to="/register" className="btn btn-dark">Sign up</Link>
          </div>
        </nav>
      </div>

      {/* HERO */}
      <div className="wrap">
        <section className="hero">
          <div className="hero-copy">
            <span className="eyebrow"><span className="dot" /> Snap → split in seconds</span>
            <h1>Stop doing <span className="strike">tax math</span> on a napkin.</h1>
            <p className="lede">Photograph any receipt — even with mixed 8% and 10% tax. Bill Analyzer reads every line item, figures out who had what, and settles the split to the yen.</p>
            <div className="hero-cta">
              <Link to="/register" className="btn btn-accent">Get started — it's free</Link>
              <span className="ghost-note">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M5 13l4 4L19 7" stroke="#1f7a55" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                Free to sign up
              </span>
            </div>
          </div>

          <div className="demo-stage">
            <button className="replay" ref={replayRef} onClick={runDemo}>↺ replay scan</button>
            <div className="receipt" ref={receiptRef}>
              <div className="scan" ref={scanRef}><div className="scan-line" /></div>
              <div className="r-pad">
                <div className="r-head">
                  <div className="r-merchant">MARUAI スーパー</div>
                  <div className="r-sub">Osaka · 2026-05-23 · ¥ JPY</div>
                </div>
                <div ref={rowsRef} />
              </div>
            </div>
            <div className="split-card" ref={splitCardRef}>
              <div className="sc-title">Split, settled</div>
              <div className="sc-person">
                <div className="sc-who"><span className="sc-av me">ME</span> You</div>
                <span className="sc-amt">¥279.75</span>
              </div>
              <div className="sc-person">
                <div className="sc-who"><span className="sc-av g">G</span> @gaurav</div>
                <span className="sc-amt">¥495.75</span>
              </div>
              <div className="sc-foot">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none"><path d="M5 13l4 4L19 7" stroke="#7fd1a6" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/></svg>
                Tax-inclusive · request sent
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* FACT BAR */}
      <div className="factbar reveal">
        <div className="wrap">
          <div className="fact"><b>~3 sec</b><span>photo → line items</span></div>
          <div className="fact"><b>8% + 10%</b><span>mixed tax handled per item</span></div>
          <div className="fact"><b>180+</b><span>currencies supported</span></div>
          <div className="fact"><b>0</b><span>spreadsheets required</span></div>
        </div>
      </div>

      {/* HOW IT WORKS */}
      <div className="wrap">
        <section id="how">
          <div className="sec-head reveal">
            <div className="sec-kicker">How it works</div>
            <h2>From crumpled receipt to settled split in three steps.</h2>
            <p>The hard part — reading messy thermal-printer text and untangling per-item tax — happens automatically.</p>
          </div>
          <div className="steps">
            <div className="step reveal">
              <div className="step-n">STEP 01</div>
              <div className="step-ic">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M3 8a2 2 0 012-2h2l1.5-2h7L17 6h2a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" stroke="#e0533d" strokeWidth="1.8"/><circle cx="12" cy="12" r="3.2" stroke="#e0533d" strokeWidth="1.8"/></svg>
              </div>
              <h3>Snap the receipt</h3>
              <p>Point your camera at any receipt. Faded, folded, foreign-language — a vision model reads it like a human would.</p>
            </div>
            <div className="step reveal">
              <div className="step-n">STEP 02</div>
              <div className="step-ic">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M7 4h10v16l-5-3-5 3V4z" stroke="#e0533d" strokeWidth="1.8" strokeLinejoin="round"/><path d="M9.5 9h5M9.5 12h3" stroke="#e0533d" strokeWidth="1.8" strokeLinecap="round"/></svg>
              </div>
              <h3>Tap who had what</h3>
              <p>Every line item appears with its real tax rate baked in. Assign each to you, a friend, or both — the math adjusts live.</p>
            </div>
            <div className="step reveal">
              <div className="step-n">STEP 03</div>
              <div className="step-ic">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M4 12a8 8 0 018-8 8 8 0 017 4M20 12a8 8 0 01-8 8 8 8 0 01-7-4" stroke="#e0533d" strokeWidth="1.8" strokeLinecap="round"/><path d="M16 8h4V4M8 16H4v4" stroke="#e0533d" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
              </div>
              <h3>Send the request</h3>
              <p>One tap fires off the exact amount owed. Net balances track who owes whom across every shared bill.</p>
            </div>
          </div>
        </section>
      </div>

      {/* WHY DIFFERENT */}
      <div className="wrap">
        <section id="why">
          <div className="wedge reveal">
            <div className="sec-kicker">Why not just use Splitwise?</div>
            <h2>Because Splitwise can't read your receipt — so it can't split by item, or get the tax right.</h2>
            <div className="compare">
              <div className="col them">
                <h4>Splitwise / bank apps</h4>
                <div className="cli"><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M6 6l12 12M18 6L6 18" stroke="#8a8378" strokeWidth="2" strokeLinecap="round"/></svg> You type every item by hand</div>
                <div className="cli"><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M6 6l12 12M18 6L6 18" stroke="#8a8378" strokeWidth="2" strokeLinecap="round"/></svg> Splits the total evenly or by guesswork</div>
                <div className="cli"><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M6 6l12 12M18 6L6 18" stroke="#8a8378" strokeWidth="2" strokeLinecap="round"/></svg> Tax is whatever you remember to add</div>
                <div className="cli"><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M6 6l12 12M18 6L6 18" stroke="#8a8378" strokeWidth="2" strokeLinecap="round"/></svg> No idea what you actually bought</div>
              </div>
              <div className="col us">
                <h4>Bill Analyzer</h4>
                <div className="cli"><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M5 13l4 4L19 7" stroke="#1f7a55" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg> Reads every line from the photo</div>
                <div className="cli"><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M5 13l4 4L19 7" stroke="#1f7a55" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg> Split per item: this is mine, that's shared</div>
                <div className="cli"><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M5 13l4 4L19 7" stroke="#1f7a55" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg> Per-item tax (8% &amp; 10%) computed exactly</div>
                <div className="cli"><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M5 13l4 4L19 7" stroke="#1f7a55" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg> Full itemized history &amp; spend insights</div>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* INSIGHTS */}
      <div className="wrap">
        <section id="insights">
          <div className="showcase">
            <div className="shot reveal"><InsightsMockup /></div>
            <div className="feat-list reveal">
              <div className="sec-kicker" style={{ marginBottom: "4px" }}>After the split</div>
              <div className="feat">
                <div className="feat-ic"><svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M4 19V5M4 19h16M8 15l3-4 3 2 4-6" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg></div>
                <div>
                  <h3>Spend that explains itself</h3>
                  <p>Every digitized receipt rolls into trends, top merchants, and category breakdowns — by day, month, or custom range.</p>
                </div>
              </div>
              <div className="feat">
                <div className="feat-ic"><svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="9" cy="8" r="3" stroke="#fff" strokeWidth="2"/><path d="M3 20a6 6 0 0112 0M16 11l2 2 4-4" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg></div>
                <div>
                  <h3>Balances that stay honest</h3>
                  <p>See exactly what you owe each friend, net across every bill. Record a payment and the balance clears itself.</p>
                </div>
              </div>
              <div className="feat">
                <div className="feat-ic"><svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 3v18M7 8h7a2.5 2.5 0 010 5H8a2.5 2.5 0 000 5h8" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg></div>
                <div>
                  <h3>Any currency, anywhere</h3>
                  <p>Yen today, euros next trip. Switch currency and every total, split, and chart follows along.</p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* FINAL CTA */}
      <div className="wrap" style={{ paddingBottom: "96px" }}>
        <div className="final reveal">
          <h2>Your next group dinner <em>splits itself.</em></h2>
          <p>Snap the receipt. Tap who had what. Send the request. That's the whole thing.</p>
          <div className="hero-cta">
            <Link to="/register" className="btn btn-accent">Get started — it's free</Link>
            <a href="#how" className="btn btn-dark">See how it works</a>
          </div>
        </div>
      </div>

      <footer>
        <div className="wrap">
          <div className="brand"><span className="mk">¥</span> Bill Analyzer</div>
          <div className="flinks">
            <a href="#how">How it works</a>
            <a href="#why">Why different</a>
            <a href="#insights">Insights</a>
            <Link to="/register">Sign up</Link>
          </div>
          <div className="muted">Snap. Split. Settled.</div>
        </div>
      </footer>
    </div>
  );
}

export const Route = createFileRoute("/")({
  component: LandingPage,
});
