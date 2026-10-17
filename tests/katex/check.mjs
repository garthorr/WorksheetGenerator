// Reads a JSON array of problem texts on stdin and renders every $...$ / $$...$$ span with
// KaTeX, exactly as the GUI's auto-render does. Prints a JSON array of failures.
import katex from "katex";

const input = JSON.parse(await new Promise((resolve) => {
  let data = "";
  process.stdin.on("data", (c) => (data += c));
  process.stdin.on("end", () => resolve(data));
}));

const failures = [];
const span = /\$\$([\s\S]+?)\$\$|\$([^$]+?)\$/g;
input.forEach((text, i) => {
  for (const m of text.matchAll(span)) {
    const tex = m[1] ?? m[2];
    try {
      katex.renderToString(tex, { displayMode: m[1] !== undefined, throwOnError: true, strict: "error" });
    } catch (e) {
      failures.push({ index: i, tex, error: String(e.message).slice(0, 200) });
    }
  }
});
console.log(JSON.stringify(failures));
