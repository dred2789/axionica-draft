import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const outDir = path.join(root, "content-structure");
const pageOrder = [
  "index.html",
  "directions.html",
  "studio.html",
  "accelerator.html",
  "capital.html",
  "services.html",
  "discovery.html",
  "product-studio.html",
  "it-consulting.html",
  "consulting.html",
  "ai-automation.html",
  "startup-tracking.html",
  "startup-packaging.html",
  "contacts.html",
  "team.html",
  "cases.html",
  "insights.html",
  "privacy.html",
  "cookies.html",
  "personal-data-consent.html",
];

const pages = [
  ...fs.readdirSync(path.join(root, "ru")).filter((file) => file.endsWith(".html")).map((file) => `ru/${file}`),
  ...fs.readdirSync(path.join(root, "en")).filter((file) => file.endsWith(".html")).map((file) => `en/${file}`),
  "404.html",
];

pages.sort((a, b) => {
  const [dirA, fileA] = a.includes("/") ? a.split("/") : ["zz", a];
  const [dirB, fileB] = b.includes("/") ? b.split("/") : ["zz", b];
  if (dirA !== dirB) return dirA.localeCompare(dirB);
  const indexA = pageOrder.indexOf(fileA);
  const indexB = pageOrder.indexOf(fileB);
  return (indexA === -1 ? 999 : indexA) - (indexB === -1 ? 999 : indexB);
});

function decodeEntities(value) {
  return value
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, "\"")
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">");
}

function cleanText(value) {
  return decodeEntities(value)
    .replace(/\s+/g, " ")
    .trim();
}

function getAttr(html, regex) {
  const match = html.match(regex);
  return match ? cleanText(match[1].trim()) : "";
}

function stripTags(html) {
  return cleanText(html.replace(/<[^>]*>/g, " "));
}

function collectLinks(scope) {
  const links = [];
  for (const match of scope.matchAll(/<a\b([^>]*)>([\s\S]*?)<\/a>/gi)) {
    const href = getAttr(match[1], /href=["']([^"']+)["']/i);
    const text = stripTags(match[2]);
    if (href && text && !links.some((link) => link.href === href && link.text === text)) {
      links.push({ text, href });
    }
  }
  return links;
}

function blockToMarkdown(html) {
  let output = html;
  output = output.replace(/<script[\s\S]*?<\/script>/gi, "");
  output = output.replace(/<style[\s\S]*?<\/style>/gi, "");
  output = output.replace(/<svg[\s\S]*?<\/svg>/gi, "");
  output = output.replace(/<span class=["']icon-badge["'][\s\S]*?<\/span>/gi, "");
  output = output.replace(/<br\s*\/?\s*>/gi, "\n");
  output = output.replace(/<a\b([^>]*)>([\s\S]*?)<\/a>/gi, (_, attrs, inner) => {
    const href = getAttr(attrs, /href=["']([^"']+)["']/i);
    const text = stripTags(inner);
    return href && text ? `${text} (${href})` : text;
  });

  for (let level = 6; level >= 1; level -= 1) {
    const hashes = "#".repeat(level + 1);
    output = output.replace(
      new RegExp(`<h${level}[^>]*>([\\s\\S]*?)<\\/h${level}>`, "gi"),
      (_, inner) => `\n\n${hashes} ${stripTags(inner)}\n`,
    );
  }

  output = output.replace(/<li[^>]*>([\s\S]*?)<\/li>/gi, (_, inner) => `\n- ${stripTags(inner)}`);
  output = output.replace(/<p[^>]*>([\s\S]*?)<\/p>/gi, (_, inner) => {
    const text = stripTags(inner);
    return text ? `\n\n${text}\n` : "";
  });
  output = output.replace(/<(section|article|div|nav|ol|ul|main|aside)[^>]*>/gi, "\n");
  output = output.replace(/<\/(section|article|div|nav|ol|ul|main|aside)>/gi, "\n");
  output = output.replace(/<[^>]*>/g, " ");
  output = decodeEntities(output);
  output = output
    .split("\n")
    .map((line) => line.trim())
    .join("\n")
    .replace(/\n{3,}/g, "\n\n");
  return output.trim();
}

function navMarkdown(html) {
  const header = (html.match(/<header[\s\S]*?<\/header>/i) || [""])[0];
  const footer = (html.match(/<footer[\s\S]*?<\/footer>/i) || [""])[0];
  const headerLinks = collectLinks(header);
  const footerLinks = collectLinks(footer);
  const lines = [];

  if (headerLinks.length) {
    lines.push("## Header Navigation", "");
    headerLinks.forEach((link) => lines.push(`- ${link.text}: ${link.href}`));
    lines.push("");
  }

  if (footerLinks.length) {
    lines.push("## Footer Navigation", "");
    footerLinks.forEach((link) => lines.push(`- ${link.text}: ${link.href}`));
  }

  return lines.join("\n").trim();
}

fs.mkdirSync(path.join(outDir, "ru"), { recursive: true });
fs.mkdirSync(path.join(outDir, "en"), { recursive: true });

const indexRows = [];
const generatedPages = [];

for (const relPath of pages) {
  const html = fs.readFileSync(path.join(root, relPath), "utf8");
  const lang =
    getAttr(html, /<html[^>]*lang=["']([^"']+)["']/i) ||
    (relPath.startsWith("ru/") ? "ru" : relPath.startsWith("en/") ? "en" : "common");
  const title = getAttr(html, /<title>([\s\S]*?)<\/title>/i);
  const description =
    getAttr(html, /<meta\s+name=["']description["'][^>]*content=["']([^"']*)["'][^>]*>/i) ||
    getAttr(html, /<meta[^>]*content=["']([^"']*)["'][^>]*name=["']description["'][^>]*>/i);
  const canonical = getAttr(html, /<link[^>]*rel=["']canonical["'][^>]*href=["']([^"']+)["']/i);
  const ogTitle = getAttr(html, /<meta[^>]*property=["']og:title["'][^>]*content=["']([^"']+)["']/i);
  const ogDescription = getAttr(
    html,
    /<meta[^>]*property=["']og:description["'][^>]*content=["']([^"']+)["']/i,
  );
  const main = (html.match(/<main[\s\S]*?<\/main>/i) || [html])[0];
  const mainLinks = collectLinks(main);
  const body = blockToMarkdown(main);
  const outRelPath = relPath.replace(/\.html$/, ".md");
  const outPath = path.join(outDir, outRelPath);

  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(
    outPath,
    [
      `# ${title || relPath}`,
      "",
      "## Page Metadata",
      "",
      `- Source HTML: ${relPath}`,
      `- Language: ${lang}`,
      `- SEO title: ${title}`,
      `- SEO description: ${description}`,
      `- Canonical: ${canonical}`,
      `- Open Graph title: ${ogTitle}`,
      `- Open Graph description: ${ogDescription}`,
      "",
      "## Content Structure",
      "",
      body || "_No main page content extracted._",
      "",
      "## Main Content Links",
      "",
      ...(mainLinks.length ? mainLinks.map((link) => `- ${link.text}: ${link.href}`) : ["_No main content links._"]),
    ].join("\n") + "\n",
    "utf8",
  );

  indexRows.push(`- [${relPath}](./${outRelPath}) - ${title}`);
  generatedPages.push({ relPath, outRelPath, title, lang });
}

const commonHtml = fs.readFileSync(path.join(root, "ru/index.html"), "utf8");
const commonContent = [
  "# Общие элементы сайта",
  "",
  "Файл фиксирует повторяемые элементы, которые встречаются на страницах сайта и важны для ИИ-агента при пересборке проекта.",
  "",
  navMarkdown(commonHtml),
  "",
  "## Global CTA",
  "",
  "- Основной CTA: Написать в Telegram",
  "- URL: https://t.me/borisovmax",
  "- Формы заявок на сайте не используются.",
  "",
  "## Legal / Requisites Placeholder",
  "",
  "- ИП Борисов Максим Андреевич",
  "- ИНН 027902102888",
  "- ОГРНИП 325028000121079.",
  "- Email: hello@borisovm.ru",
].join("\n") + "\n";

fs.writeFileSync(path.join(outDir, "_common.md"), commonContent, "utf8");

const masterBrief = [
  "# Axionica Master Brief",
  "",
  "Единый структурированный бриф по текстовому контенту сайта Axionica. Файл собирает общие элементы, SEO-метаданные, контентную структуру, CTA и ссылки всех HTML-страниц проекта.",
  "",
  "## Назначение",
  "",
  "- Использовать как единое ТЗ для ИИ-агента по созданию или пересборке сайта.",
  "- Не заменяет исходные документы проекта, а агрегирует текущую текстовую структуру страниц.",
  "- При изменении HTML-страниц должен обновляться вместе с отдельными файлами в `content-structure/`.",
  "",
  "## Источники правды",
  "",
  "1. `Prompt.md`",
  "2. `Концепция бренда.md`",
  "3. `Венчурная экосистема полного цикла.md`",
  "",
  "## Общие Элементы",
  "",
  commonContent.replace(/^# Общие элементы сайта\n+/, "").trim(),
  "",
  "## Индекс Страниц",
  "",
  ...generatedPages.map((page) => `- ${page.relPath} -> ${page.outRelPath} - ${page.title}`),
  "",
  "## Контент Страниц",
  "",
];

for (const page of generatedPages) {
  const pageContent = fs.readFileSync(path.join(outDir, page.outRelPath), "utf8").trim();
  masterBrief.push(`### ${page.relPath}`, "", pageContent.replace(/^# /, "#### "), "");
}

fs.writeFileSync(path.join(outDir, "master-brief.md"), masterBrief.join("\n") + "\n", "utf8");

fs.writeFileSync(
  path.join(outDir, "README.md"),
  [
    "# Текстовая структура страниц Axionica",
    "",
    "Эта папка содержит Markdown-выгрузку контента текущего сайта. Файлы можно использовать как текстовое ТЗ для ИИ-агента, который будет создавать или пересобирать сайт.",
    "",
    "## Как читать",
    "",
    "- Каждый файл соответствует HTML-странице из проекта.",
    "- В начале файла указаны SEO-метаданные и исходный HTML-файл.",
    "- Раздел `Content Structure` содержит текстовую структуру основного содержимого страницы.",
    "- Раздел `Main Content Links` фиксирует CTA и внутренние ссылки внутри основного контента.",
    "- Общие элементы навигации, футера и глобального CTA вынесены в [`_common.md`](./_common.md).",
    "- Единый собранный бриф по всему контенту находится в [`master-brief.md`](./master-brief.md).",
    "",
    "## Источники правды",
    "",
    "При изменении текстов сохраняется приоритет документов из корня проекта:",
    "",
    "1. `Prompt.md`",
    "2. `Концепция бренда.md`",
    "3. `Венчурная экосистема полного цикла.md`",
    "",
    "## Обязательная синхронизация с HTML",
    "",
    "Если в проекте изменяется, добавляется или удаляется любая HTML-страница, соответствующие `.md` файлы в этой папке и `master-brief.md` должны быть обновлены в том же изменении.",
    "",
    "- При изменении текста, SEO-метаданных, CTA, ссылок или структуры секций в HTML нужно обновить соответствующий Markdown-файл и `master-brief.md`.",
    "- При добавлении новой HTML-страницы нужно добавить для нее новый `.md` файл в `content-structure/ru/`, `content-structure/en/` или в корень папки, если страница общая, а также добавить страницу в `master-brief.md`.",
    "- При удалении HTML-страницы нужно удалить или явно пометить устаревшим соответствующий Markdown-файл и убрать или пометить страницу в `master-brief.md`.",
    "- Если меняются общие элементы сайта, навигация, footer, глобальный CTA или реквизиты, нужно обновить `_common.md` и соответствующий раздел в `master-brief.md`.",
    "- Для полной механической пересборки выгрузки можно использовать команду `node scripts/export-content-structure.mjs`.",
    "",
    "Markdown-файлы в `content-structure/` и `master-brief.md` считаются обязательной текстовой спецификацией сайта, а не вспомогательными черновиками.",
    "",
    "## Страницы",
    "",
    ...indexRows,
  ].join("\n") + "\n",
  "utf8",
);

console.log(`Exported ${pages.length} pages to ${path.relative(root, outDir)}`);
