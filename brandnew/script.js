const translations = {
  ru: {
    navWork: "Что делаем",
    navMethod: "Подход",
    navContact: "Контакт",
    heroEyebrow: "Product studio / discovery / IT consulting",
    heroTitle: "Запускаем IT-продукты без хаоса в разработке, бюджете и следующих шагах",
    heroText:
      "Axionica соединяет продуктовую логику, разработку и взгляд на экономику проекта. Помогаем компаниям и стартапам понять, что строить, как строить и как не потерять управляемость после первого релиза.",
    primaryCta: "Написать в Telegram",
    secondaryCta: "Посмотреть формат",
    panelStudio: "Discovery, MVP, product delivery",
    panelAccelerator: "Tracking, packaging, growth logic",
    panelCapital: "Transparency, risk and exit readiness",
    introEyebrow: "Коротко",
    introTitle: "Не просто разработка. Технологический партнер на стыке продукта, delivery и денег.",
    introText:
      "Сейчас Axionica практично помогает с discovery, заказной разработкой, product studio и IT-консалтингом. Акселерация и инвестиционная логика показаны как направление развития бренда, без обещаний доходности и публичного предложения инвестирования.",
    workEyebrow: "Доступно сейчас",
    workTitle: "С чего можно начать",
    serviceOneTitle: "Discovery / аудит",
    serviceOneText: "Прояснить scope, риски, архитектуру, приоритеты и бюджет до старта разработки.",
    serviceTwoTitle: "Заказная разработка / Product Studio",
    serviceTwoText: "Собрать продуктовый и технический контур, когда задача уже достаточно понятна.",
    serviceThreeTitle: "IT-консалтинг",
    serviceThreeText: "Вернуть прозрачность в delivery, архитектуру, процессы и управленческие решения.",
    methodEyebrow: "Как работаем",
    methodTitle: "Сначала ясность, потом разработка, затем рост",
    methodText:
      "Такой порядок снижает риск бессмысленного бюджета: сначала фиксируются ограничения и решения, затем команда входит в реализацию с понятным ритмом, критериями и следующей точкой развития.",
    stepOne: "Понять задачу, риски и экономику",
    stepTwo: "Собрать scope, роли и критерии решений",
    stepThree: "Запустить разработку прозрачно и управляемо",
    stepFour: "Оценить готовность к росту и следующему этапу",
    proofOne: "лет совокупного опыта команды в продукте, delivery и операционном росте",
    proofTwo: "продуктов и стартапов в опыте основателя и команды",
    proofThree: "форм заявок, фальшивых кейсов и агрессивной продажи",
    contactEyebrow: "Контакт",
    contactTitle: "Если задача уже есть, короткий разговор быстрее длинной формы.",
    contactText:
      "Можно прийти с идеей, спорным scope, проблемой в текущей разработке или вопросом, что делать до старта.",
    contactCta: "Обсудить проект в Telegram",
    footerLegal: "ИП Борисов Максим Андреевич. Реквизиты перед публикацией можно заменить."
  },
  en: {
    navWork: "What we do",
    navMethod: "Method",
    navContact: "Contact",
    heroEyebrow: "Product studio / discovery / IT consulting",
    heroTitle: "We launch digital products with clear delivery, budgets and next steps",
    heroText:
      "Axionica connects product thinking, development and project economics. We help companies and startups decide what to build, how to build it and how to stay in control after the first release.",
    primaryCta: "Message on Telegram",
    secondaryCta: "See the format",
    panelStudio: "Discovery, MVP, product delivery",
    panelAccelerator: "Tracking, packaging, growth logic",
    panelCapital: "Transparency, risk and exit readiness",
    introEyebrow: "In short",
    introTitle: "Not just development. A technology partner across product, delivery and money.",
    introText:
      "Today Axionica works practically on discovery, custom development, product studio and IT consulting. Acceleration and investment logic are shown as the brand's direction of development, without return promises or a public investment offer.",
    workEyebrow: "Available now",
    workTitle: "Where to start",
    serviceOneTitle: "Discovery / audit",
    serviceOneText: "Clarify scope, risks, architecture, priorities and budget before development starts.",
    serviceTwoTitle: "Custom development / Product Studio",
    serviceTwoText: "Build the product and technical delivery setup when the task is already clear enough.",
    serviceThreeTitle: "IT consulting",
    serviceThreeText: "Bring transparency back to delivery, architecture, processes and management decisions.",
    methodEyebrow: "How we work",
    methodTitle: "Clarity first, then development, then growth",
    methodText:
      "This order lowers the risk of wasted budget: constraints and decisions are fixed first, then the team moves into delivery with a clear rhythm, criteria and next development point.",
    stepOne: "Understand the task, risks and economics",
    stepTwo: "Define scope, roles and decision criteria",
    stepThree: "Run delivery transparently and under control",
    stepFour: "Assess readiness for growth and the next stage",
    proofOne: "years of combined team experience across product, delivery and operating growth",
    proofTwo: "products and startups in the founder's and team's experience",
    proofThree: "lead forms, fake cases and aggressive sales patterns",
    contactEyebrow: "Contact",
    contactTitle: "If the task already exists, a short conversation is faster than a long form.",
    contactText: "Come with an idea, disputed scope, delivery issue or a question about what to do before building.",
    contactCta: "Discuss on Telegram",
    footerLegal: "Sole proprietor Maksim Borisov. Legal details can be replaced before publication."
  }
};

const langButtons = document.querySelectorAll(".lang-button");
const translatable = document.querySelectorAll("[data-i18n]");

function setLanguage(lang) {
  const dictionary = translations[lang] || translations.ru;
  document.documentElement.lang = lang;

  translatable.forEach((node) => {
    const key = node.dataset.i18n;
    if (dictionary[key]) {
      node.textContent = dictionary[key];
    }
  });

  langButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.lang === lang);
  });

  const url = new URL(window.location.href);
  if (lang === "en") {
    url.searchParams.set("lang", "en");
  } else {
    url.searchParams.delete("lang");
  }
  window.history.replaceState({}, "", url);
}

langButtons.forEach((button) => {
  button.addEventListener("click", () => setLanguage(button.dataset.lang));
});

const initialLang = new URLSearchParams(window.location.search).get("lang") === "en" ? "en" : "ru";
setLanguage(initialLang);
