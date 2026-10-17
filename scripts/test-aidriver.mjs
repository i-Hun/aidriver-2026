// Проверки данных раздела /stories/aidriver-2026: посты канала, слаги, экранирование,
// ссылки и согласованность статистики. Запускается `npm test` на каждый push/PR.
import assert from "node:assert/strict";
import fs from "node:fs";

const read = (p) => JSON.parse(fs.readFileSync(new URL(p, import.meta.url), "utf8"));
const data = read("../data/aidriver-2026.json");
const page = fs.readFileSync(
  new URL("../pages/stories/aidriver-2026.vue", import.meta.url),
  "utf8",
);

const HALLS = { big: "Большой зал", small: "Малый зал" };

// --- событие ---------------------------------------------------------------
for (const key of ["title", "subtitle", "date", "place", "programUrl", "channelUrl", "sourceNote"]) {
  assert(
    typeof data.event?.[key] === "string" && data.event[key].trim() !== "",
    "event." + key + " пустое",
  );
}
assert.match(data.event.programUrl, /^https:\/\//, "event.programUrl");
assert.match(data.event.channelUrl, /^https:\/\/t\.me\//, "event.channelUrl");

// --- дата и статистика -----------------------------------------------------
assert.ok(!Number.isNaN(Date.parse(data.updated)), "updated не парсится");
assert.match(data.updated, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z)$/, "updated без смещения");
assert.equal(typeof data.live, "boolean", "live не boolean");
assert.ok(Array.isArray(data.talks) && data.talks.length > 0, "talks пуст");
assert.equal(data.stats.talks, data.talks.length, "stats.talks ≠ числу постов");
assert.equal(
  data.stats.halls,
  new Set(data.talks.map((t) => t.hall).filter(Boolean)).size,
  "stats.halls ≠ числу залов",
);
assert.equal(data.stats.withPost, data.talks.length, "stats.withPost ≠ числу постов");

// --- посты -----------------------------------------------------------------
const slugs = new Set();
const ids = new Set();
const ALLOWED_TAGS = new Set(["p", "ul", "li", "strong", "code", "a"]);

for (const t of data.talks) {
  const where = t.slug || t.title;
  assert.ok(t.hall === "" || HALLS[t.hall], where + ": неизвестный зал " + t.hall);
  if (t.hall) assert.equal(t.hallLabel, HALLS[t.hall], where + ": hallLabel");
  assert.match(t.time, /^\d{2}:\d{2}–\d{2}:\d{2}$/, where + ": time");
  assert.match(
    t.slug,
    new RegExp("^" + (t.hall || "talk") + "-" + t.time.slice(0, 2) + t.time.slice(3, 5) + "-\\d+$"),
    where + ": слаг не выводится из зала, времени и message_id",
  );
  assert.ok(!slugs.has(t.slug), where + ": слаг повторяется");
  slugs.add(t.slug);

  assert.ok(t.title.trim().length > 0, where + ": пустой заголовок");
  assert.ok(t.speaker.trim().length > 0, where + ": пустой спикер");
  assert.ok(Number.isInteger(t.messageId), where + ": messageId не число");
  assert.ok(!ids.has(t.messageId), where + ": messageId повторяется");
  ids.add(t.messageId);
  assert.equal(t.url, "https://t.me/ai_n_ns/" + t.messageId, where + ": url ≠ messageId");

  assert.ok(typeof t.bodyHtml === "string" && t.bodyHtml.length > 200, where + ": пустой текст поста");
  assert.doesNotMatch(t.bodyHtml, /<script|<img|onerror=|javascript:/i, where + ": небезопасный HTML");
  for (const m of t.bodyHtml.matchAll(/<\/?([a-z]+)/gi)) {
    assert.ok(ALLOWED_TAGS.has(m[1].toLowerCase()), where + ": тег <" + m[1] + "> не разрешён");
  }
  assert.doesNotMatch(t.bodyHtml, /\*\*|\]\(/, where + ": в HTML осталась markdown-разметка");

  assert.ok(t.preview.length > 0, where + ": пустой preview");
  assert.ok(t.preview.length <= 701, where + ": preview длиннее 700 символов");
  assert.match(t.preview, /[.!?…]$/, where + ": preview обрывается на полуслове");
  assert.doesNotMatch(t.preview, /[`*]/, where + ": в preview осталась разметка");
  assert.doesNotMatch(t.preview, /^—/, where + ": preview начинается с тире");

  assert.ok(Array.isArray(t.tags), where + ": tags не массив");
  for (const tag of t.tags) assert.match(tag, /^[A-Za-zА-Яа-я0-9_]+$/, where + ": тег " + tag);
}

// --- страница --------------------------------------------------------------
assert.ok(page.includes('"../../data/aidriver-2026.json"'), "страница не импортирует данные слоя относительно");
assert.ok(page.includes('"../../assets/styles/design-tokens.css"'), "страница не подключает токены слоя");
assert.doesNotMatch(page, /~~\//, "в странице остались абсолютные импорты сайта (~~/)");
assert.ok(page.includes("/stories/recsys-2026"), "потеряна ссылка на путеводитель RecSys 2026");
assert.ok(page.includes("t.bodyHtml"), "страница не выводит текст поста");
// adblock-фильтры скрывают классы ad/ad-*; раздел обязан жить на conf-*.
assert.doesNotMatch(page, /class="ad(-|\s|")/, "в разметке остались adblock-классы ad-*");
assert.doesNotMatch(page, /\.ad(?=[\s{,:])/, "в стилях остались adblock-классы .ad*");

console.log("aidriver-2026: PASS, " + data.talks.length + " постов");
