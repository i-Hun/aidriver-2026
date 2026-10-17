// Проверки данных раздела /stories/aidriver-2026: структура, слаги, метки, экранирование,
// ссылки на посты и согласованность статистики. Запускается `npm test` на каждый push/PR.
import assert from "node:assert/strict";
import fs from "node:fs";

const read = (p) => JSON.parse(fs.readFileSync(new URL(p, import.meta.url), "utf8"));
const data = read("../data/aidriver-2026.json");
const page = fs.readFileSync(
  new URL("../pages/stories/aidriver-2026.vue", import.meta.url),
  "utf8",
);

const HALLS = { big: "Большой зал", small: "Малый зал" };
const LABELS = [
  "Что показали",
  "Что ещё прозвучало",
  "Метод/архитектура",
  "Бенчмарки",
  "Вопросы и направления",
  "Что взять в наш проект",
  "Оговорки",
  "Формулировка",
];

// Тот же рендер, что в scripts/aidriver_site_data.py: экранирование и `code`-разметка.
const expectedHtml = (text) =>
  text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/`([^`]+)`/g, "<code>$1</code>");

// --- событие ---------------------------------------------------------------
for (const key of [
  "title",
  "subtitle",
  "date",
  "place",
  "programUrl",
  "channelUrl",
  "sourceNote",
]) {
  assert(
    typeof data.event?.[key] === "string" && data.event[key].trim() !== "",
    "event." + key + " пустое",
  );
}
assert.match(data.event.programUrl, /^https:\/\//, "event.programUrl");
assert.match(data.event.channelUrl, /^https:\/\/t\.me\//, "event.channelUrl");

// --- дата и статистика -----------------------------------------------------
assert.ok(!Number.isNaN(Date.parse(data.updated)), "updated не парсится");
assert.match(
  data.updated,
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z)$/,
  "updated без смещения",
);
assert.equal(typeof data.live, "boolean", "live не boolean");
assert.ok(Array.isArray(data.talks) && data.talks.length > 0, "talks пуст");
assert.equal(data.stats.talks, data.talks.length, "stats.talks ≠ числу докладов");
assert.equal(
  data.stats.halls,
  new Set(data.talks.map((t) => t.hall)).size,
  "stats.halls ≠ числу залов",
);
assert.equal(
  data.stats.withPost,
  data.talks.filter((t) => t.post).length,
  "stats.withPost ≠ числу докладов с постом",
);

// --- доклады ---------------------------------------------------------------
const slugs = new Set();
for (const t of data.talks) {
  const where = t.slug || t.title;
  assert.ok(HALLS[t.hall], where + ": неизвестный зал " + t.hall);
  assert.equal(t.hallLabel, HALLS[t.hall], where + ": hallLabel");
  assert.match(t.time, /^\d{2}:\d{2}–\d{2}:\d{2}$/, where + ": time");
  assert.equal(
    t.slug,
    t.hall + "-" + t.time.slice(0, 2) + t.time.slice(3, 5),
    where + ": слаг не выводится из зала и времени",
  );
  assert.ok(!slugs.has(t.slug), where + ": слаг повторяется");
  slugs.add(t.slug);

  assert.ok(t.title.trim().length > 0, where + ": пустой заголовок");
  assert.ok(t.speaker.trim().length > 0, where + ": пустой спикер");
  assert.ok(Array.isArray(t.items) && t.items.length >= 4, where + ": меньше 4 пунктов");

  for (const it of t.items) {
    assert.ok(LABELS.includes(it.label), where + ": неизвестная метка " + it.label);
    assert.ok(it.text.trim().length > 0, where + ": пустой текст пункта");
    assert.equal(it.html, expectedHtml(it.text), where + ": html ≠ экранированному тексту");
    assert.doesNotMatch(
      it.html,
      /<script|<img|onerror=|javascript:/i,
      where + ": небезопасный HTML",
    );
  }

  const labels = t.items.map((it) => it.label);
  assert.equal(new Set(labels).size, labels.length, where + ": метка повторяется");

  assert.ok(t.lead.length > 0, where + ": пустой lead");
  assert.ok(t.lead.length <= 321, where + ": lead длиннее 320 символов");
  assert.doesNotMatch(t.lead, /[`*]/, where + ": в lead осталась разметка");

  if (t.post) {
    assert.ok(Number.isInteger(t.post.messageId), where + ": messageId не число");
    assert.equal(
      t.post.url,
      "https://t.me/ai_n_ns/" + t.post.messageId,
      where + ": url поста не совпадает с messageId",
    );
  }

  assert.ok(Array.isArray(t.tags), where + ": tags не массив");
  for (const tag of t.tags) {
    assert.match(tag, /^[A-Za-zА-Яа-я0-9_]+$/, where + ": тег " + tag);
  }
}

// --- страница --------------------------------------------------------------
assert.ok(
  page.includes('"../../data/aidriver-2026.json"'),
  "страница не импортирует данные слоя относительно",
);
assert.ok(
  page.includes('"../../assets/styles/design-tokens.css"'),
  "страница не подключает токены слоя",
);
assert.doesNotMatch(page, /~~\//, "в странице остались абсолютные импорты сайта (~~/)");
assert.ok(
  page.includes("/stories/recsys-2026"),
  "потеряна ссылка на путеводитель RecSys 2026",
);

console.log("aidriver-2026: PASS, " + data.talks.length + " докладов");
