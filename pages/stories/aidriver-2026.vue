<script setup>
// Раздел «AI Driver & RecSys 2026 — доклады»: список разборов докладов конференции.
// Данные собирает scripts/aidriver_site_data.py из волта; страница их только показывает.
import "../../assets/styles/design-tokens.css";
import talksData from "../../data/aidriver-2026.json";

definePageMeta({ layout: "default" });

const page = talksData;

const event = computed(() => page?.event || {});
const talks = computed(() => page?.talks || []);
const stats = computed(() => page?.stats || { talks: 0, halls: 0, withPost: 0 });
const live = computed(() => Boolean(page?.live));

const hall = ref("all");
const query = ref("");

const halls = computed(() => {
  const seen = new Map();
  for (const t of talks.value) if (!seen.has(t.hall)) seen.set(t.hall, t.hallLabel);
  return [...seen.entries()].map(([id, label]) => ({ id, label }));
});

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase();
  return talks.value.filter((t) => {
    if (hall.value !== "all" && t.hall !== hall.value) return false;
    if (!q) return true;
    const hay = [t.title, t.speaker, t.org, ...(t.items || []).map((i) => i.text)]
      .join(" ")
      .toLowerCase();
    return hay.includes(q);
  });
});

const updated = computed(() => {
  const iso = page?.updated;
  if (!iso) return "";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Moscow",
  }).format(new Date(iso));
});

useHead(() => ({
  title: "AI Driver & RecSys 2026 — доклады",
  htmlAttrs: { lang: "ru" },
  meta: [
    {
      name: "description",
      content:
        "Разборы докладов конференции AI Driver & RecSys 2026 (Сбер, 17 октября 2026): методы, числа из выступлений и границы применимости.",
    },
    { property: "og:title", content: "AI Driver & RecSys 2026 — доклады" },
    {
      property: "og:description",
      content: "Разборы докладов конференции Сбера по рекомендательным системам: методы, числа, ограничения.",
    },
    { property: "og:type", content: "website" },
  ],
}));
</script>

<template>
  <div class="conf">
    <header class="conf-hero">
      <p class="conf-eyebrow">Конференция · {{ event.date }}</p>
      <h1>{{ event.title }}</h1>
      <p class="conf-lead">{{ event.subtitle }}</p>
      <ul class="conf-meta">
        <li v-if="event.place">{{ event.place }}</li>
        <li>{{ stats.talks }} докладов · два зала</li>
        <li v-if="updated">обновлено {{ updated }} MSK</li>
        <li v-if="live" class="conf-live">идёт</li>
      </ul>
      <div class="conf-actions">
        <a class="conf-btn" :href="event.programUrl" target="_blank" rel="noopener">Программа конференции</a>
        <a class="conf-btn conf-btn-ghost" :href="event.channelUrl" target="_blank" rel="noopener">Канал @ai_n_ns</a>
        <NuxtLink class="conf-btn conf-btn-ghost" to="/stories/recsys-2026">Путеводитель по RecSys 2026</NuxtLink>
      </div>
      <p class="conf-note">{{ event.sourceNote }}</p>
    </header>

    <section class="conf-controls" aria-label="Фильтры">
      <div class="conf-tabs" role="tablist">
        <button
          class="conf-tab"
          :class="{ 'is-on': hall === 'all' }"
          role="tab"
          :aria-selected="hall === 'all'"
          @click="hall = 'all'"
        >
          Все залы
        </button>
        <button
          v-for="h in halls"
          :key="h.id"
          class="conf-tab"
          :class="{ 'is-on': hall === h.id }"
          role="tab"
          :aria-selected="hall === h.id"
          @click="hall = h.id"
        >
          {{ h.label }}
        </button>
      </div>
      <input
        v-model="query"
        class="conf-search"
        type="search"
        placeholder="Поиск по докладу, спикеру, тексту"
        aria-label="Поиск по докладам"
      />
    </section>

    <p class="conf-count">
      {{ filtered.length }} <template v-if="filtered.length === 1">доклад</template>
      <template v-else-if="filtered.length > 1 && filtered.length < 5">доклада</template>
      <template v-else>докладов</template>
    </p>

    <section class="conf-grid">
      <article v-for="t in filtered" :key="t.slug" class="conf-card">
        <div class="conf-card-top">
          <span class="conf-time">{{ t.time }}</span>
          <span class="conf-hall">{{ t.hallLabel }}</span>
        </div>
        <h2>{{ t.title }}</h2>
        <p class="conf-speaker">
          {{ t.speaker }}<template v-if="t.org"> · {{ t.org }}</template>
        </p>
        <p class="conf-preview">{{ t.lead }}</p>

        <details class="conf-more">
          <summary>Полный разбор</summary>
          <div v-for="it in t.items" :key="it.label" class="conf-item">
            <h3>{{ it.label }}</h3>
            <p v-html="it.html"></p>
          </div>
        </details>

        <div class="conf-links">
          <a v-if="t.post" :href="t.post.url" target="_blank" rel="noopener">Пост в канале →</a>
          <span v-if="t.tags && t.tags.length" class="conf-tags">
            <span v-for="tag in t.tags" :key="tag" class="conf-tag">#{{ tag }}</span>
          </span>
        </div>
      </article>
    </section>

    <p v-if="!filtered.length" class="conf-empty">Ничего не нашлось — сбросьте фильтр или запрос.</p>
  </div>
</template>

<style scoped>
.conf {
  max-width: var(--page);
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg) calc(var(--space-xl) * 2);
  color: var(--color-ink);
  font-family: var(--font-sans);
  font-size: var(--text-body-sm);
  line-height: var(--leading-body);
}

.conf-hero {
  padding: var(--space-xl) 0 var(--space-lg);
  border-bottom: 1px solid var(--color-rule);
}
.conf-eyebrow {
  margin: 0 0 var(--space-sm);
  color: var(--color-accent);
  font-size: var(--text-label);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.conf-hero h1 {
  margin: 0 0 var(--space-md);
  font-size: clamp(2rem, 4vw, 3rem);
  line-height: 1.1;
  letter-spacing: -0.02em;
}
.conf-lead {
  max-width: 46rem;
  margin: 0 0 var(--space-md);
  color: var(--color-muted);
  font-size: var(--text-body);
}
.conf-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs) var(--space-lg);
  margin: 0 0 var(--space-lg);
  padding: 0;
  list-style: none;
  color: var(--color-muted);
  font-size: var(--text-meta);
}
.conf-meta li + li::before {
  content: "·";
  margin-right: 6px;
  color: var(--color-rule);
}
.conf-live {
  color: var(--color-live);
  font-weight: 600;
}
.conf-live::before {
  content: "● ";
}
.conf-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}
.conf .conf-btn {
  display: inline-flex;
  align-items: center;
  min-height: var(--tap);
  padding: 0 var(--space-lg);
  border: 0;
  border-radius: var(--radius-pill);
  background: linear-gradient(120deg, var(--color-grad-a), var(--color-grad-b));
  color: #FFFFFF;
  font-size: var(--text-button);
  font-weight: 600;
  text-decoration: none;
  box-shadow: var(--shadow-accent);
}
.conf .conf-btn-ghost {
  background: transparent;
  color: var(--color-ink);
  border: 1px solid var(--color-muted);
  box-shadow: none;
}
.conf-btn:hover {
  transform: translateY(-1px);
}
.conf-note {
  max-width: 46rem;
  margin: var(--space-lg) 0 0;
  color: var(--color-muted);
  font-size: var(--text-meta);
}

.conf-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  padding: var(--space-lg) 0 var(--space-sm);
}
.conf-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
}
.conf-tab {
  min-height: var(--tap);
  padding: 0 var(--space-md);
  border: 1px solid var(--color-rule);
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  color: var(--color-muted);
  font: inherit;
  font-size: var(--text-button);
  cursor: pointer;
}
.conf-tab.is-on {
  border-color: transparent;
  background: var(--color-accent);
  color: #FFFFFF;
  font-weight: 600;
}
.conf-search {
  flex: 1 1 18rem;
  min-height: var(--tap);
  padding: 0 var(--space-md);
  border: 1px solid var(--color-rule);
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  color: var(--color-ink);
  font: inherit;
  font-size: var(--text-button);
}
.conf-search::placeholder {
  color: var(--color-muted);
}
.conf-count {
  margin: var(--space-sm) 0 var(--space-md);
  color: var(--color-muted);
  font-size: var(--text-meta);
}

.conf-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 22rem), 1fr));
  gap: var(--space-md);
}
.conf-card {
  display: flex;
  flex-direction: column;
  padding: var(--space-lg);
  border: 1px solid var(--color-rule);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  box-shadow: var(--shadow-1);
}
.conf-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  margin-bottom: var(--space-sm);
  font-size: var(--text-label);
}
.conf-time {
  font-variant-numeric: tabular-nums;
  color: var(--color-accent);
  font-weight: 600;
  letter-spacing: 0.02em;
}
.conf-hall {
  padding: 2px 10px;
  border-radius: var(--radius-pill);
  background: var(--color-tint);
  color: var(--color-ink);
}
.conf-card h2 {
  margin: 0 0 var(--space-xs);
  font-size: var(--text-h1);
  line-height: 1.28;
  letter-spacing: -0.01em;
}
.conf-speaker {
  margin: 0 0 var(--space-md);
  color: var(--color-muted);
  font-size: var(--text-meta);
}
.conf-preview {
  margin: 0 0 var(--space-md);
}
.conf-more {
  margin-top: auto;
  border-top: 1px solid var(--color-rule);
  padding-top: var(--space-sm);
}
.conf-more summary {
  min-height: var(--tap);
  display: flex;
  align-items: center;
  color: var(--color-accent);
  font-size: var(--text-button);
  font-weight: 600;
  cursor: pointer;
  list-style: none;
}
.conf-more summary::-webkit-details-marker {
  display: none;
}
.conf-more summary::after {
  content: "+";
  margin-left: auto;
  font-size: 1.1rem;
}
.conf-more[open] summary::after {
  content: "−";
}
.conf-item h3 {
  margin: var(--space-md) 0 var(--space-xs);
  color: var(--color-muted);
  font-size: var(--text-label);
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.conf-item p {
  margin: 0;
  font-size: var(--text-body-sm);
}
.conf-item :deep(code) {
  padding: 1px 5px;
  border-radius: 6px;
  background: var(--color-tint);
  font-size: 0.92em;
}
.conf-links {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  margin-top: var(--space-md);
  font-size: var(--text-meta);
}
.conf-links a {
  color: var(--color-accent);
  font-weight: 600;
  text-decoration: none;
}
.conf-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.conf-tag {
  color: var(--color-muted);
}
.conf-empty {
  padding: var(--space-xl) 0;
  color: var(--color-muted);
}

@media (max-width: 640px) {
  .conf {
    padding: var(--space-lg) var(--space-md) var(--space-xl);
  }
  .conf-btn,
  .conf-search {
    width: 100%;
    justify-content: center;
  }
}
</style>
