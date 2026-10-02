const form = document.querySelector("#analyze-form");
const textarea = document.querySelector("#claim-text");
const button = document.querySelector("#submit-button");
const output = document.querySelector("#output");

function addText(parent, tag, text, className) {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  parent.append(node);
  return node;
}

function showResult(data) {
  output.replaceChildren();
  const heading = document.createElement("div");
  heading.className = "result-head";
  addText(heading, "span", data.verdict, "badge");
  addText(heading, "strong", `${data.results.length} claim${data.results.length === 1 ? "" : "s"} found`);
  output.append(heading);
  addText(output, "p", data.summary, "summary");

  for (const result of data.results) {
    const article = document.createElement("article");
    article.className = "claim";
    addText(article, "strong", result.verdict.toUpperCase());
    addText(article, "p", result.claim.text);
    addText(article, "small", result.rationale);
    addText(
      article,
      "small",
      `Evidence confidence: ${(result.confidence * 100).toFixed(0)}% (not a calibrated probability)`,
    );
    if (result.claim.signals.length) {
      addText(article, "small", `Review signals: ${result.claim.signals.join(", ")}`);
    }
    if (result.evidence.length) {
      const sources = document.createElement("ul");
      for (const item of result.evidence) {
        const source = document.createElement("li");
        const link = document.createElement("a");
        link.href = item.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = `${item.source} · ${item.supports}`;
        source.append(link);
        if (item.published_at) {
          addText(source, "small", ` · ${item.published_at}`);
        }
        addText(source, "p", item.snippet);
        sources.append(source);
      }
      article.append(sources);
    }
    output.append(article);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  output.replaceChildren();
  button.disabled = true;
  button.textContent = "Analyzing...";
  try {
    const response = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: textarea.value }),
    });
    const data = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail[0]?.msg
        : data.detail;
      throw new Error(detail || "Request failed.");
    }
    showResult(data);
  } catch (error) {
    addText(output, "p", error.message || "Could not reach the analysis service.", "error");
  } finally {
    button.disabled = false;
    button.textContent = "Analyze text";
  }
});
