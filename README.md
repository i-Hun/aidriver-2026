# AI Driver & RecSys 2026 — доклады

Исходники раздела [nagornyy.me/stories/aidriver-2026](https://nagornyy.me/stories/aidriver-2026):
разборы докладов конференции Сбера по рекомендательным системам (17 октября 2026, Москва),
собранные по записи двух потоков и её расшифровке.

Нашли ошибку в разборе, неверное число или хотите что-то предложить — [откройте issue](../../issues/new/choose)
или пришлите pull request. Сайт пересобирается сам после каждого merge в `main`, обычно за несколько минут.

## Что где лежит

| Путь | Что это |
|---|---|
| `data/aidriver-2026.json` | данные страницы: событие, статистика, 14 карточек (спикер, зал, время, пункты разбора, пост в канале) |
| `pages/stories/aidriver-2026.vue` | страница раздела (Vue, Nuxt 4) |
| `assets/styles/design-tokens.css` | дизайн-токены, общие с остальным сайтом |
| `scripts/aidriver_site_data.py` | генератор данных из волта заметок (см. ниже) |
| `scripts/test-aidriver.mjs` | проверки данных, которые CI запускает на каждый pull request |

## Запустить локально

Нужен Node.js 22.

```sh
npm ci
npm test        # проверки данных
npm run dev     # http://localhost:3000/stories/aidriver-2026
```

Репозиторий — [слой Nuxt](https://nuxt.com/docs/getting-started/layers): сайт подключает его
git-сабмодулем и `extends`, а сам по себе он запускается как отдельное приложение только с этим разделом.

## Данные

Тексты разборов ведутся в заметках автора, генератор собирает из них `data/aidriver-2026.json`.

```sh
python3 scripts/aidriver_site_data.py --check   # статистика и расхождения, без записи
python3 scripts/aidriver_site_data.py           # обновить data/aidriver-2026.json
```

По умолчанию генератор читает `~/.hermes/workspace/notes/projects/Статьи`; другой каталог
задаётся переменной `AIDRIVER_NOTES`.

Обновления во время конференции приезжают сами: правка данных в `main` этого репозитория
через workflow `deploy-site` просит сайт сдвинуть сабмодуль, и Netlify пересобирает страницу.
