"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const DIFF = { 1: "Easy", 2: "Medium", 3: "Hard" };
const DRAFT_KEY = "worksheet-draft-v1";
const COURSE_KEY = "worksheet-course-filter";
const COURSE_SHORT = { alg1: "Algebra 1", geo: "Geometry", alg2: "Algebra 2", precalc: "Precalc", calc: "Calculus",
  conceptual: "Conceptual", ap1: "AP Physics 1" };
const LEVEL_LETTER = { 1: "E", 2: "M", 3: "H" };
// Section defaults when a topic is added from a course's view of the catalog.
const COURSE_DEFAULTS = { conceptual: { g: 10, nice: true } };

const state = {
  topics: [],
  topicById: {},
  settings: {},
  courses: [],
  courseFilter: "all",
  sheet: null, // { id?, title, instructions, seed, sections: [{ config, problems, error }] }
};

// ------------------------------------------------------------------ utils

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
    body: opts.body && typeof opts.body !== "string" ? JSON.stringify(opts.body) : opts.body,
  });
  if (res.status === 401) { location.href = "/login"; throw new Error("Not logged in"); }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    throw new Error(Array.isArray(d) ? d.map((e) => `${e.loc?.slice(-1)[0]}: ${e.msg}`).join("; ") : d || res.statusText);
  }
  return data;
}

function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v === true) e.setAttribute(k, "");
    else if (v !== false && v != null) e.setAttribute(k, v);
  }
  for (const c of children.flat()) if (c != null) e.append(c instanceof Node ? c : document.createTextNode(c));
  return e;
}

// ---- Clean-up for AI text that left LaTeX outside $...$ (mirrors _tidy_math in app/ai.py, which
// fixes new problems on the server; this keeps worksheets saved before that fix readable).
const UNICODE = { times: "×", cdot: "·", pm: "±", mp: "∓", approx: "≈", leq: "≤", le: "≤", geq: "≥", ge: "≥",
  neq: "≠", ne: "≠", circ: "°", degree: "°", infty: "∞", to: "→", rightarrow: "→", Rightarrow: "⇒", implies: "⇒",
  pi: "π", theta: "θ", mu: "μ", Delta: "Δ", delta: "δ", alpha: "α", beta: "β", gamma: "γ", omega: "ω", Omega: "Ω",
  lambda: "λ", rho: "ρ", sigma: "σ", tau: "τ", phi: "φ", epsilon: "ε", left: "", right: "", quad: " ", qquad: " ",
  displaystyle: "" };
const SUPERSCRIPT = { 0: "⁰", 1: "¹", 2: "²", 3: "³", 4: "⁴", 5: "⁵", 6: "⁶", 7: "⁷", 8: "⁸", 9: "⁹", "-": "⁻", "+": "⁺" };

function latexToText(t) {
  for (let i = 0; i < 3; i++) {
    t = t.replace(/\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}/g, (m, a, b, off, all) => {
      const simple = /^[\w.]+$/.test(a) && /^[\w.]+$/.test(b);
      const f = simple ? `${a}/${b}` : `(${a})/(${b})`;
      return simple && /[\w(]/.test(all[off + m.length] || "") ? `(${f})` : f;
    });
    t = t.replace(/\\sqrt\{([^{}]*)\}/g, (m, a) => (/^[\w.]+$/.test(a) ? `√${a}` : `√(${a})`));
    t = t.replace(/\\(?:text|mathrm|mathbf|textbf|operatorname)\{([^{}]*)\}/g, "$1");
  }
  t = t.replace(/\^\{?([-+]?\d+)\}?/g, (m, d) => [...d].map((c) => SUPERSCRIPT[c]).join(""));
  t = t.replace(/\^\{([^{}]*)\}/g, "^($1)").replace(/_\{([^{}]*)\}/g, "_$1").replace(/\\[,;:! ]/g, " ");
  t = t.replace(/\\([A-Za-z]+)/g, (m, name, off, all) => {
    const fn = ["sin", "cos", "tan", "ln", "log"].includes(name);
    return (fn && off && /\w/.test(all[off - 1]) ? " " : "") + (UNICODE[name] ?? name);
  });
  return t.replace(/\\(?!\$)/g, ""); // keep escaped dollars (\$5)
}

function tidyMath(s) {
  s = s.replace(/\\n(?!(?:u|eq|e|ot|abla|eg|i|leq|geq|mid|parallel|ewline|oindent)\b)/g, "\n");
  if (!s.includes("$") && /\\[A-Za-z]+|\^|_\{/.test(s)) {
    const words = s.replace(/\\[A-Za-z]+(\{[^{}]*\})?/g, " ").match(/\b[A-Za-z]{4,}\b/g) || [];
    if (words.length <= 2 && !s.includes("\n") && s.length <= 80) return `$${s.trim().replace(/°/g, "^\\circ")}$`;
  }
  return s.replace(/(\$\$[\s\S]+?\$\$|\$[^$]+\$)|([^$]+)/g, (m, math, text) => math || latexToText(text));
}

/** A problem's figure. As an <img>, the SVG can't run script even if a saved worksheet was altered. */
function figureImg(svg) {
  return el("img", { class: "figure", alt: "Figure for this problem", src: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}` });
}

/** Stop a line break from separating inline math from the punctuation after it ("v" / "."). */
function keepPunctuationWithMath(root) {
  for (const katexEl of root.querySelectorAll(".katex:not(.katex-display .katex)")) {
    // auto-render wraps each formula in its own <span>; the punctuation sits next to that wrapper
    const parent = katexEl.parentElement;
    const k = parent !== root && parent.tagName === "SPAN" && parent.childNodes.length === 1 ? parent : katexEl;
    const next = k.nextSibling;
    const m = next?.nodeType === Node.TEXT_NODE && next.textContent.match(/^[.,;:?!)]+/);
    if (!m) continue;
    next.textContent = next.textContent.slice(m[0].length);
    const wrap = el("span", { class: "nobr" });
    k.replaceWith(wrap);
    wrap.append(k, m[0]);
  }
}

/** Render text with $..$ / $$..$$ math. Text is inserted as text, never HTML. */
function mathText(tag, text, cls) {
  const e = el(tag, { class: cls }, tidyMath(text || ""));
  if (window.renderMathInElement) {
    renderMathInElement(e, {
      delimiters: [{ left: "$$", right: "$$", display: true }, { left: "$", right: "$", display: false }],
      throwOnError: false,
    });
    keepPunctuationWithMath(e);
  }
  return e;
}

function setStatus(msg, kind = "", spinner = false) {
  const s = $("#status");
  s.hidden = !msg;
  s.className = `status no-print ${kind}`;
  s.replaceChildren(...(spinner ? [el("span", { class: "spinner" })] : []), msg || "");
}

function saveDraft() {
  try { localStorage.setItem(DRAFT_KEY, JSON.stringify(state.sheet)); } catch { /* storage unavailable */ }
}

function loadDraft() {
  try { return JSON.parse(localStorage.getItem(DRAFT_KEY) || "null"); } catch { return null; }
}

function newSheet() {
  return { title: state.settings.default_title || "Practice Worksheet", instructions: "", seed: null, sections: [] };
}

function topicLabel(cfg) {
  return cfg.topic === "custom" ? cfg.custom_topic : state.topicById[cfg.topic]?.name || cfg.topic;
}

// ------------------------------------------------------------------ navigation

function showView(name) {
  $$(".nav").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  $$(".view").forEach((v) => (v.hidden = v.id !== `view-${name}`));
  if (name === "library") loadLibrary();
  if (name === "setup") fillSettingsForm();
}

// ------------------------------------------------------------------ topic catalog

function renderCourseChips() {
  const wrap = $("#course-filter");
  const chips = [["all", "All"], ...state.courses.map((c) => [c.id, COURSE_SHORT[c.id] || c.name])];
  wrap.replaceChildren(...chips.map(([id, label]) => el("button", {
    class: `chip ${state.courseFilter === id ? "active" : ""}`,
    title: id === "all" ? "Every topic" : state.courses.find((c) => c.id === id).name,
    onclick: () => {
      state.courseFilter = id;
      try { localStorage.setItem(COURSE_KEY, id); } catch { /* storage unavailable */ }
      renderCourseChips();
      renderCatalog();
    },
  }, label)));
}

function renderCatalog() {
  const q = $("#topic-search").value.trim().toLowerCase();
  const course = state.courseFilter;
  const list = $("#topic-list");
  list.replaceChildren();
  const shown = state.topics.filter((t) => (course === "all" || t.courses.includes(course)) &&
    (!q || [t.name, t.description, t.category, ...t.skills.map((s) => s.label)].join(" ").toLowerCase().includes(q)));
  // Group by unit, in order of first appearance (and by subject in the all-courses view).
  const groups = new Map();
  for (const t of shown) {
    const key = course === "all" ? `${t.subject}|${t.category}` : t.category;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(t);
  }
  // In a course view, units follow the course's teaching order.
  const units = state.courses.find((c) => c.id === course)?.units || [];
  const rank = (key) => (units.includes(key) ? units.indexOf(key) : units.length);
  const ordered = [...groups].sort(([a], [b]) => rank(a) - rank(b));
  for (const [, topics] of ordered) {
    const t0 = topics[0];
    list.append(el("div", { class: "cat-head" },
      course === "all" ? el("span", { class: "subj" }, t0.subject === "math" ? "Math" : "Physics") : null,
      course === "all" ? "·" : null, t0.category));
    for (const t of topics) {
      list.append(el("button", {
        class: "topic", title: `Add a "${t.name}" section`,
        onclick: (ev) => { addSection({ subject: t.subject, topic: t.id, course: course === "all" ? "" : course,
          ...COURSE_DEFAULTS[course] });
          ev.currentTarget.classList.add("flash");
          setTimeout(() => ev.currentTarget?.classList.remove("flash"), 600); },
      }, el("span", { class: "name" }, t.name), el("span", { class: "desc" }, t.description),
      course === "all" ? el("span", { class: "courses" }, t.courses.map((c) => COURSE_SHORT[c]).join(" · ")) : null,
      el("span", { class: "add" }, "+")));
    }
  }
  if (!shown.length) list.append(el("p", { class: "hint" }, "No matching topics — add it as a custom AI topic below."));
}

// ------------------------------------------------------------------ sections (builder)

function addSection(partial) {
  const cfg = {
    title: "", subject: "math", topic: "", custom_topic: "", count: 5, difficulty: 2,
    source: "builtin", ai_prompt: "", skills: null, g: null, nice: null, answer_form: null, places: null,
    figures: null, format: "free", course: "", ...partial,
  };
  if (cfg.topic === "custom") cfg.source = "ai";
  state.sheet.sections.push({ config: cfg, problems: [], error: "" });
  renderSections();
  renderPreview();
  saveDraft();
}

// Multiple choice is for AP Physics 1 only: sections added from the AP Physics 1 view, or topics
// that only AP Physics 1 has. Built-in problems only.
function mcAllowed(cfg) {
  const t = state.topicById[cfg.topic];
  if (!t?.mc || cfg.source !== "builtin") return false;
  return cfg.course === "ap1" || (t.courses.length === 1 && t.courses[0] === "ap1");
}

function topicSelect(cfg, onchange) {
  const sel = el("select", { "aria-label": "Topic", onchange });
  const groups = {};
  for (const t of state.topics) {
    const key = `${t.subject === "math" ? "Math" : "Physics"} · ${t.category}`;
    groups[key] ??= el("optgroup", { label: key });
    groups[key].append(el("option", { value: t.id, selected: t.id === cfg.topic }, t.name));
  }
  sel.append(...Object.values(groups));
  sel.append(el("optgroup", { label: "AI" }, el("option", { value: "custom", selected: cfg.topic === "custom" }, "✨ Custom topic…")));
  return sel;
}

function seg(options, value, onpick, extraCls = "") {
  const s = el("div", { class: `seg full ${extraCls}` });
  for (const [val, label, cls] of options) {
    s.append(el("button", {
      type: "button", class: `${cls || ""} ${String(val) === String(value) ? "active" : ""}`,
      onclick: () => onpick(val),
    }, label));
  }
  return s;
}

/** The difficulty level used for a topic: the requested one, else the closest (harder on ties). */
function nearestLevel(levels, d) {
  return [...levels].sort((a, b) => Math.abs(a - d) - Math.abs(b - d) || b - a)[0];
}

/** Skill ids a section will draw from: its chosen skills, else every skill at the difficulty. */
function effectiveSkills(cfg, t) {
  if (cfg.skills?.length) return new Set(cfg.skills);
  const lv = nearestLevel(t.levels, cfg.difficulty);
  return new Set(t.skills.filter((s) => s.levels.includes(lv)).map((s) => s.id));
}

function skillPicker(cfg, t, update) {
  const active = effectiveSkills(cfg, t);
  const auto = effectiveSkills({ ...cfg, skills: null }, t);
  const toggle = (id) => {
    const next = new Set(active);
    next.has(id) ? next.delete(id) : next.add(id);
    const ids = t.skills.map((s) => s.id).filter((s) => next.has(s));
    const same = ids.length === auto.size && ids.every((s) => auto.has(s));
    update({ skills: ids.length && !same ? ids : null });
  };
  const chips = t.skills.map((s) => el("button", {
    type: "button", class: `chip skill ${active.has(s.id) ? "active" : ""}`,
    title: `${s.label} — ${s.levels.map((l) => DIFF[l]).join(", ")}`,
    onclick: () => toggle(s.id),
  }, s.label, el("span", { class: "lv" }, s.levels.map((l) => LEVEL_LETTER[l]).join(""))));
  const status = cfg.skills?.length
    ? el("span", { class: "hint" }, "custom mix · ", el("a", { href: "#", onclick: (e) => { e.preventDefault(); update({ skills: null }); } }, "reset"))
    : el("span", { class: "hint" }, `all ${DIFF[cfg.difficulty].toLowerCase()} skills`);
  return el("div", { class: "skills-field" },
    el("div", { class: "skills-head" }, el("span", {}, "Skills"), status),
    el("div", { class: "chips skills" }, ...chips));
}

function answerOptions(cfg, t, update) {
  const form = cfg.answer_form ?? state.settings.math_answer_form;
  const places = cfg.places ?? state.settings.math_places;
  const showForm = !t || t.exact_forms, showRound = (!t || t.rounding) && !(showForm && form === "exact");
  if (!showForm && !showRound) return null;
  return el("div", { class: "grid answer-opts" },
    showForm ? el("label", { title: "Exact answers use π and simplest radical form" }, "Answers",
      seg([["exact", "Exact"], ["both", "Both"], ["decimal", "Decimal"]], form, (v) => update({ answer_form: v }))) : null,
    showRound ? el("label", { title: "Decimal answers are rounded to this place" }, "Round to",
      seg([[0, "1"], [1, "0.1"], [2, "0.01"], [3, "0.001"]], places, (v) => update({ places: v }))) : null);
}

function renderSections() {
  const wrap = $("#sections");
  wrap.replaceChildren();
  const secs = state.sheet.sections;
  $("#sections-empty").hidden = secs.length > 0;
  const total = secs.reduce((n, s) => n + Number(s.config.count || 0), 0);
  $("#problem-total").textContent = secs.length ? `${total} problem${total === 1 ? "" : "s"}` : "";

  secs.forEach((sec, i) => {
    const cfg = sec.config;
    const update = (patch, rerenderPreview = false) => {
      Object.assign(cfg, patch);
      if (cfg.topic === "custom") cfg.source = "ai";
      const t = state.topicById[cfg.topic];
      if (t) cfg.subject = t.subject;
      if (!mcAllowed(cfg)) cfg.format = "free";
      saveDraft();
      renderSections();
      if (rerenderPreview) renderPreview();
    };
    const move = (d) => {
      const j = i + d;
      if (j < 0 || j >= secs.length) return;
      [secs[i], secs[j]] = [secs[j], secs[i]];
      saveDraft(); renderSections(); renderPreview();
    };

    const card = el("div", { class: "section-card" },
      el("div", { class: "top" },
        el("span", { class: "num" }, `${i + 1}`),
        topicSelect(cfg, (e) => { sec.problems = []; sec.error = ""; update({ topic: e.target.value, title: "", skills: null }, true); }),
        el("button", { class: "btn icon small", title: "Move up", onclick: () => move(-1), disabled: i === 0 }, "↑"),
        el("button", { class: "btn icon small", title: "Move down", onclick: () => move(1), disabled: i === secs.length - 1 }, "↓"),
        el("button", { class: "btn icon small danger", title: "Remove section",
          onclick: () => { secs.splice(i, 1); saveDraft(); renderSections(); renderPreview(); } }, "✕")),
    );

    if (cfg.topic === "custom") {
      card.append(el("div", { class: "grid" },
        el("label", {}, "Subject",
          el("select", { onchange: (e) => update({ subject: e.target.value }) },
            el("option", { value: "math", selected: cfg.subject === "math" }, "Math"),
            el("option", { value: "physics", selected: cfg.subject === "physics" }, "Physics"))),
        el("label", {}, "Custom topic",
          el("input", { value: cfg.custom_topic, placeholder: "Describe the topic",
            onchange: (e) => { sec.problems = []; update({ custom_topic: e.target.value }, true); } }))));
    } else if (state.topicById[cfg.topic]) {
      card.append(el("p", { class: "hint" }, state.topicById[cfg.topic].description));
    }

    card.append(
      el("div", { class: "grid" },
        el("label", {}, "Count",
          el("input", { type: "number", min: 1, max: 50, value: cfg.count,
            onchange: (e) => update({ count: Math.max(1, Math.min(50, Number(e.target.value) || 1)) }) })),
        el("label", {}, "Difficulty",
          seg([[1, "Easy"], [2, "Medium"], [3, "Hard"]], cfg.difficulty, (v) => update({ difficulty: v, skills: null })))),
      el("label", {}, "Source",
        cfg.topic === "custom"
          ? el("span", { class: "hint" }, "Custom topics are written by AI (Ollama).")
          : seg([["builtin", "Built-in (exact)"], ["ai", "✨ AI (Ollama)", "ai"]], cfg.source, (v) => update({ source: v }))),
    );
    const topicMeta = state.topicById[cfg.topic];
    if (mcAllowed(cfg)) {
      card.append(el("label", { title: "AP-style multiple choice: four choices, one correct, wrong choices from common mistakes" },
        "Format", seg([["free", "Free response"], ["mc", "Multiple choice"]], cfg.format || "free",
          (v) => { sec.problems = []; update({ format: v }, true); })));
    }
    if (topicMeta && topicMeta.skills.length > 1) card.append(skillPicker(cfg, topicMeta, update));
    if (cfg.subject === "math" && (cfg.source === "ai" || topicMeta)) {
      const opts = answerOptions(cfg, cfg.source === "ai" ? null : topicMeta, update);
      if (opts) card.append(opts);
    }
    if (topicMeta?.figures && cfg.source === "builtin") {
      const on = cfg.figures ?? state.settings.figures;
      card.append(el("label", { title: "Problems that are read off a graph or diagram always keep their figure" }, "Figures",
        seg([[true, "Show"], [false, "Hide"]], on, (v) => update({ figures: v }))));
    }
    if (cfg.subject === "physics") {
      // null = follow the Setup page default
      const g = cfg.g ?? state.settings.physics_g, nice = cfg.nice ?? state.settings.physics_nice;
      card.append(el("div", { class: "grid physics-opts" },
        el("label", { title: "Gravitational acceleration used in the problems" }, "g (m/s²)",
          seg([[9.8, "9.8"], [10, "10"]], g, (v) => update({ g: v }))),
        el("label", { title: "Whole numbers: simple givens and answers, e.g. for conceptual physics" }, "Numbers",
          seg([[false, "Realistic"], [true, "Whole"]], nice, (v) => update({ nice: v })))));
    }
    if (cfg.source === "ai") {
      card.append(el("label", {}, "AI instructions (optional)",
        el("input", { value: cfg.ai_prompt, placeholder: "e.g. word problems about sports",
          onchange: (e) => update({ ai_prompt: e.target.value }) })));
    }
    card.append(el("label", {}, "Section heading (optional)",
      el("input", { value: cfg.title, placeholder: topicLabel(cfg) || "",
        onchange: (e) => { cfg.title = e.target.value; saveDraft(); renderPreview(); } })));
    if (sec.error) card.append(el("p", { class: "err" }, sec.error));
    card.append(el("div", { class: "row", style: "justify-content:flex-end;margin-bottom:6px" },
      el("button", { class: "btn small", onclick: () => generateSections([i]) },
        sec.problems.length ? "↻ Regenerate section" : "Generate section")));
    wrap.append(card);
  });
}

// ------------------------------------------------------------------ generation

function validateConfigs(indices) {
  for (const i of indices) {
    const c = state.sheet.sections[i].config;
    if (!c.topic) return `Section ${i + 1}: pick a topic.`;
    if (c.topic === "custom" && !c.custom_topic.trim()) return `Section ${i + 1}: describe the custom topic.`;
  }
  return "";
}

async function generateSections(indices, seed = null) {
  const err = validateConfigs(indices);
  if (err) { setStatus(err, "error"); return; }
  const usesAI = indices.some((i) => state.sheet.sections[i].config.source === "ai");
  const btn = $("#generate");
  btn.disabled = true;
  setStatus(usesAI ? "Generating… AI sections can take a minute or two." : "Generating…", "", true);
  try {
    // Questions in the other sections, so the new ones don't repeat them.
    const avoid = state.sheet.sections.filter((_, i) => !indices.includes(i))
      .flatMap((s) => s.problems.map((p) => p.key || p.question));
    const res = await api("/api/generate", {
      method: "POST",
      body: { seed, avoid, sections: indices.map((i) => state.sheet.sections[i].config) },
    });
    res.sections.forEach((out, k) => {
      const sec = state.sheet.sections[indices[k]];
      sec.error = out.error;
      if (!out.error) sec.problems = out.problems;
    });
    if (indices.length === state.sheet.sections.length) {
      state.sheet.seed = res.seed;
      $("#ws-seed").value = res.seed;
    }
    const errors = res.sections.filter((s) => s.error).length;
    const flagged = res.sections.flatMap((s) => s.problems).filter((p) => p.verified === false).length;
    if (errors) setStatus(`${errors} section(s) failed — see the section card for details.`, "error");
    else if (flagged) setStatus(`Done. ${flagged} AI answer(s) failed the formula check — marked ⚠ for review.`, "error");
    else setStatus(`Done${indices.length === state.sheet.sections.length ? ` · seed ${res.seed}` : ""}.`, "ok");
  } catch (e) {
    setStatus(`Generation failed: ${e.message}`, "error");
  } finally {
    btn.disabled = false;
    saveDraft();
    renderSections();
    renderPreview();
  }
}

async function regenerateProblem(si, pi) {
  const sec = state.sheet.sections[si];
  setStatus("Regenerating problem…", "", true);
  try {
    const avoid = state.sheet.sections.flatMap((s) => s.problems.map((p) => p.key || p.question));
    sec.problems[pi] = await api("/api/problem", { method: "POST", body: { ...sec.config, avoid } });
    setStatus("");
    saveDraft();
    renderPreview();
  } catch (e) {
    setStatus(`Could not regenerate: ${e.message}`, "error");
  }
}

// ------------------------------------------------------------------ preview

function badge(p) {
  if (p.source !== "ai") return null;
  if (p.verified === true) return el("span", { class: "tag ok badge", title: p.check_note }, "AI ✓");
  if (p.verified === false) return el("span", { class: "tag warn badge", title: p.check_note }, "AI ⚠ check");
  return el("span", { class: "tag unk badge", title: p.check_note }, "AI ?");
}

function sheetHeader(isKey) {
  const s = state.settings, sh = state.sheet;
  const frag = [];
  if (s.header_line) frag.push(el("div", { class: "ws-header" }, el("span", {}, s.header_line)));
  frag.push(el("div", { class: "ws-title" }, (sh.title || "Worksheet") + (isKey ? " — Answer Key" : "")));
  if (!isKey && s.show_name_date) frag.push(el("div", { class: "ws-meta" }, el("span", {}, "Name:"), el("span", {}, "Date:")));
  if (!isKey && sh.instructions) frag.push(el("div", { class: "ws-instructions" }, sh.instructions));
  return frag;
}

function renderPreview() {
  const s = state.settings, sh = state.sheet;
  const sheet = $("#paper-sheet"), key = $("#paper-key");
  for (const p of [sheet, key]) {
    p.className = `paper ${p === key ? "key" : ""} ${s.paper === "a4" ? "a4" : ""} ${Number(s.columns) === 2 && p === sheet ? "cols-2" : ""}`;
    p.replaceChildren(...sheetHeader(p === key));
  }
  if (!sh.sections.length) {
    sheet.append(el("p", { class: "empty" }, "Add topics from the catalog, then click Generate."));
    return;
  }
  let n = 0;
  sh.sections.forEach((sec, si) => {
    const heading = sec.config.title || topicLabel(sec.config);
    const sDiv = el("div", { class: "ws-section" }, el("h4", {}, heading));
    const kDiv = el("div", { class: "ws-section" }, el("h4", {}, heading));
    const grid = el("div", { class: "problems" });
    if (!sec.problems.length) {
      sDiv.append(sec.error
        ? el("p", { class: "sec-error" }, sec.error)
        : el("p", { class: "placeholder" }, `${sec.config.count} × ${DIFF[sec.config.difficulty]} — not generated yet`));
    }
    sec.problems.forEach((p, pi) => {
      n += 1;
      const q = mathText("div", p.question, "q");
      if (p.figure) q.append(figureImg(p.figure));
      if (p.choices?.length) q.append(choiceList(p.choices));
      const b = badge(p);
      if (b) q.append(b);
      const tools = el("div", { class: "ptools" },
        el("button", { title: "New problem", onclick: () => regenerateProblem(si, pi) }, "↻"),
        el("button", { title: "Edit", onclick: () => editProblem(si, pi) }, "✎"),
        el("button", { title: "Delete", onclick: () => { sec.problems.splice(pi, 1); saveDraft(); renderPreview(); } }, "✕"));
      const prob = el("div", { class: "problem" }, el("span", { class: "n" }, `${n}.`), q, tools);
      if (s.work_space && s.work_space !== "none") prob.append(el("div", { class: `work ${s.work_space}` }));
      grid.append(prob);

      const item = el("div", { class: "key-item" }, el("span", { class: "n" }, `${n}.`), mathText("div", p.answer, "a"));
      if (s.key_solutions && p.solution) item.append(mathText("div", p.solution, "s"));
      if (p.source === "ai" && p.verified !== true) item.append(el("div", { class: "note" }, p.check_note));
      kDiv.append(item);
    });
    if (sec.problems.length) sDiv.append(grid);
    sheet.append(sDiv);
    key.append(kDiv);
  });
  document.getElementById("page-style").textContent =
    `@page { size: ${s.paper === "a4" ? "A4" : "letter"}; margin: 0.6in 0.65in; }`;
}

function choiceList(choices) {
  return el("ol", { class: "choices" }, ...choices.map((c, i) =>
    el("li", {}, el("span", { class: "letter" }, `(${"ABCD"[i]})`), mathText("span", `$\\displaystyle ${c}$`))));
}

// ------------------------------------------------------------------ edit dialog

function editProblem(si, pi) {
  const p = state.sheet.sections[si].problems[pi];
  const dlg = $("#edit-dialog");
  $("#edit-q").value = p.question;
  $("#edit-a").value = p.answer;
  $("#edit-s").value = p.solution || "";
  $("#edit-choices-row").hidden = !p.choices?.length;
  $("#edit-choices").value = (p.choices || []).join("\n");
  $("#edit-figure-row").hidden = !p.figure;
  $("#edit-keep-figure").checked = true;
  const choices = () => $("#edit-choices").value.split("\n").map((c) => c.trim()).filter(Boolean);
  const preview = () => $("#edit-preview").replaceChildren(
    mathText("div", $("#edit-q").value), ...(p.choices?.length ? [choiceList(choices())] : []),
    el("hr"), mathText("div", "Answer: " + $("#edit-a").value));
  preview();
  ["#edit-q", "#edit-a", "#edit-choices"].forEach((id) => ($(id).oninput = preview));
  dlg.onclose = () => {
    if (dlg.returnValue !== "save") return;
    Object.assign(p, { question: $("#edit-q").value, answer: $("#edit-a").value, solution: $("#edit-s").value });
    if (p.choices?.length) {
      p.choices = choices();
      const letter = /^\(([A-D])\)/.exec(p.answer.trim());  // the key's letter, e.g. "(B) 12 m/s"
      p.correct = letter ? "ABCD".indexOf(letter[1]) : null;
    }
    if (p.figure && !$("#edit-keep-figure").checked) p.figure = "";
    if (p.source === "ai") { p.verified = null; p.check_note = "Edited by hand."; }
    saveDraft();
    renderPreview();
  };
  dlg.returnValue = "";
  dlg.showModal();
}

// ------------------------------------------------------------------ save / export / print

async function saveSheet() {
  try {
    const saved = await api("/api/worksheets", { method: "POST", body: state.sheet });
    state.sheet.id = saved.id;
    saveDraft();
    setStatus(`Saved “${saved.title}” to the library.`, "ok");
  } catch (e) {
    setStatus(`Save failed: ${e.message}`, "error");
  }
}

function exportJSON() {
  const blob = new Blob([JSON.stringify(state.sheet, null, 2)], { type: "application/json" });
  const a = el("a", { href: URL.createObjectURL(blob), download: `${(state.sheet.title || "worksheet").replace(/[^\w-]+/g, "_")}.json` });
  a.click();
  URL.revokeObjectURL(a.href);
}

function printSheet() {
  const what = $("#print-what").value;
  document.body.classList.toggle("print-sheet", what === "sheet");
  document.body.classList.toggle("print-key", what === "key");
  window.print();
}

// ------------------------------------------------------------------ library

async function loadLibrary() {
  const rows = $("#library-rows");
  const list = await api("/api/worksheets");
  $("#library-empty").hidden = list.length > 0;
  rows.replaceChildren(...list.map((w) => el("tr", {},
    el("td", {}, w.title || "(untitled)"),
    el("td", {}, String(w.problems)),
    el("td", {}, new Date(w.updated * 1000).toLocaleString()),
    el("td", {},
      el("button", { class: "btn small", onclick: () => openSheet(w.id) }, "Open"), " ",
      el("button", { class: "btn small", onclick: () => openSheet(w.id, true) }, "Duplicate"), " ",
      el("button", { class: "btn small danger", onclick: async () => {
        if (!confirm(`Delete “${w.title}”?`)) return;
        await api(`/api/worksheets/${w.id}`, { method: "DELETE" });
        loadLibrary();
      } }, "Delete")))));
}

async function openSheet(id, duplicate = false) {
  const sheet = await api(`/api/worksheets/${id}`);
  if (duplicate) { delete sheet.id; sheet.title = `${sheet.title} (copy)`; }
  state.sheet = sheet;
  syncSheetFields();
  saveDraft();
  showView("build");
  renderSections();
  renderPreview();
}

function syncSheetFields() {
  $("#ws-title").value = state.sheet.title || "";
  $("#ws-instructions").value = state.sheet.instructions || "";
  $("#ws-seed").value = state.sheet.seed || "";
}

// ------------------------------------------------------------------ setup

async function fillSettingsForm() {
  const f = $("#settings-form");
  const s = state.settings;
  for (const [k, v] of Object.entries(s)) {
    const input = f.elements[k];
    if (!input) continue;
    if (input.type === "checkbox") input.checked = !!v;
    else if (input.tagName !== "SELECT" || k !== "ollama_model") input.value = v;
  }
  setModelOptions([], s.ollama_model);
  testOllama();
}

function setModelOptions(models, current) {
  const sel = $("#model-select");
  const all = [...new Set([...(current ? [current] : []), ...models])];
  sel.replaceChildren(...all.map((m) => el("option", { value: m, selected: m === current },
    models.length && !models.includes(m) ? `${m} (not pulled)` : m)));
}

async function testOllama() {
  const out = $("#ollama-status");
  const url = $("#settings-form").elements.ollama_url.value;
  out.className = "status";
  out.replaceChildren(el("span", { class: "spinner" }), `Contacting ${url}…`);
  const r = await api(`/api/ollama/status?url=${encodeURIComponent(url)}`).catch((e) => ({ ok: false, error: e.message, models: [] }));
  const current = $("#model-select").value || state.settings.ollama_model;
  setModelOptions(r.models, current);
  if (r.ok) {
    out.className = "status ok";
    out.textContent = `Connected · ${r.models.length} model(s) available.` +
      (r.models.includes(current) ? "" : ` “${current}” is not pulled — run: ollama pull ${current}`);
  } else {
    out.className = "status error";
    out.textContent = `Cannot reach Ollama: ${r.error}`;
  }
}

async function saveSettings(ev) {
  ev.preventDefault();
  const f = ev.target;
  const body = {};
  for (const input of f.elements) {
    if (!input.name) continue;
    if (input.type === "checkbox") body[input.name] = input.checked;
    else if (input.type === "number" || ["columns", "physics_g", "math_places"].includes(input.name)) body[input.name] = Number(input.value);
    else body[input.name] = input.value;
  }
  try {
    state.settings = await api("/api/settings", { method: "PUT", body });
    $("#settings-saved").textContent = "Saved ✓";
    setTimeout(() => ($("#settings-saved").textContent = ""), 2000);
    renderPreview();
  } catch (e) {
    $("#settings-saved").textContent = `Error: ${e.message}`;
  }
}

// ------------------------------------------------------------------ boot

async function boot() {
  document.head.append(el("style", { id: "page-style" }));
  const [topics, settings, session, courses] = await Promise.all(
    [api("/api/topics"), api("/api/settings"), api("/api/session"), api("/api/courses")]);
  state.courses = courses;
  try { state.courseFilter = localStorage.getItem(COURSE_KEY) || "all"; } catch { /* storage unavailable */ }
  if (state.courseFilter !== "all" && !courses.some((c) => c.id === state.courseFilter)) state.courseFilter = "all";
  $("#logout-link").hidden = !session.auth;
  state.topics = topics;
  state.topicById = Object.fromEntries(topics.map((t) => [t.id, t]));
  state.settings = settings;
  state.sheet = loadDraft() || newSheet();
  // Drop sections whose built-in topic no longer exists.
  state.sheet.sections = state.sheet.sections.filter((s) => s.config.topic === "custom" || state.topicById[s.config.topic]);

  $$(".nav").forEach((b) => (b.onclick = () => showView(b.dataset.view)));
  $("#topic-search").oninput = renderCatalog;
  renderCourseChips();
  $("#add-custom").onclick = () => {
    const text = $("#custom-topic-input").value.trim();
    if (!text) { $("#custom-topic-input").focus(); return; }
    addSection({ subject: $("#custom-subject").value, topic: "custom", custom_topic: text, source: "ai" });
    $("#custom-topic-input").value = "";
  };
  $("#custom-topic-input").onkeydown = (e) => { if (e.key === "Enter") $("#add-custom").click(); };
  $("#ws-title").oninput = (e) => { state.sheet.title = e.target.value; saveDraft(); renderPreview(); };
  $("#ws-instructions").oninput = (e) => { state.sheet.instructions = e.target.value; saveDraft(); renderPreview(); };
  $("#seed-random").onclick = () => ($("#ws-seed").value = Math.floor(Math.random() * 999999) + 1);
  $("#generate").onclick = () => {
    if (!state.sheet.sections.length) { setStatus("Add at least one topic first.", "error"); return; }
    const seed = Number($("#ws-seed").value) || null;
    generateSections(state.sheet.sections.map((_, i) => i), seed);
  };
  $$("#preview-mode button").forEach((b) => (b.onclick = () => {
    $$("#preview-mode button").forEach((x) => x.classList.toggle("active", x === b));
    $(".preview-wrap").classList.toggle("mode-sheet", b.dataset.mode === "sheet");
    $(".preview-wrap").classList.toggle("mode-key", b.dataset.mode === "key");
  }));
  $(".preview-wrap").classList.add("mode-sheet");
  $("#print").onclick = printSheet;
  $("#save").onclick = saveSheet;
  $("#export").onclick = exportJSON;
  $("#settings-form").onsubmit = saveSettings;
  $("#test-ollama").onclick = testOllama;
  window.addEventListener("afterprint", () => document.body.classList.remove("print-sheet", "print-key"));

  syncSheetFields();
  renderCatalog();
  renderSections();
  renderPreview();
}

// KaTeX loads with `defer` before this script, so it is ready here.
boot().catch((e) => setStatus(`Failed to load: ${e.message}`, "error"));
