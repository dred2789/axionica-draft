const navToggle = document.querySelector("[data-nav-toggle]");
const navMenu = document.querySelector("[data-nav]");
const navDropdowns = document.querySelectorAll("[data-nav-dropdown]");
const siteHeader = document.querySelector(".site-header");
const prefersReducedMotion = window.matchMedia(
  "(prefers-reduced-motion: reduce)"
).matches;

/* ---------- Active nav link ---------- */
if (navMenu) {
  const currentPath = window.location.pathname;
  const currentFile = currentPath.endsWith("/")
    ? "index.html"
    : currentPath.split("/").pop();
  const navLinks = navMenu.querySelectorAll(".nav-links a");

  navLinks.forEach((link) => {
    const linkFile =
      new URL(link.getAttribute("href"), window.location.href).pathname
        .split("/")
        .pop() || "index.html";
    const isCurrent = linkFile === currentFile;

    link.classList.toggle("is-active", isCurrent);

    if (isCurrent) {
      link.setAttribute("aria-current", "page");

      const parentDropdown = link.closest("[data-nav-dropdown]");

      if (parentDropdown) {
        const parentToggle = parentDropdown.querySelector(
          ".nav-dropdown-toggle"
        );

        parentDropdown.classList.add("is-active");

        if (parentToggle) {
          parentToggle.setAttribute("data-active", "true");
        }
      }
    } else {
      link.removeAttribute("aria-current");
    }
  });
}

/* ---------- Mobile menu + dropdowns ---------- */
if (navToggle && navMenu) {
  const closeDropdowns = () => {
    navDropdowns.forEach((dropdown) => {
      dropdown.open = false;
    });
  };

  const setMenuState = (isOpen) => {
    navMenu.dataset.open = String(isOpen);
    navMenu.classList.toggle("is-open", isOpen);
    navToggle.setAttribute("aria-expanded", String(isOpen));

    if (!isOpen) {
      closeDropdowns();
    }
  };

  navToggle.addEventListener("click", () => {
    const isOpen = navMenu.dataset.open === "true";
    setMenuState(!isOpen);
  });

  navDropdowns.forEach((dropdown) => {
    dropdown.addEventListener("toggle", () => {
      if (dropdown.open) {
        navDropdowns.forEach((otherDropdown) => {
          if (otherDropdown !== dropdown) {
            otherDropdown.open = false;
          }
        });
      }
    });
  });

  navMenu.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      if (window.innerWidth <= 899) {
        setMenuState(false);
      } else {
        closeDropdowns();
      }
    });
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 899) {
      setMenuState(false);
    }
  });

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setMenuState(false);
    }
  });

  document.addEventListener("click", (event) => {
    if (!navMenu.contains(event.target) && !navToggle.contains(event.target)) {
      closeDropdowns();
    }
  });
}

/* ---------- Header state on scroll ---------- */
if (siteHeader) {
  const onScroll = () => {
    siteHeader.classList.toggle("is-scrolled", window.scrollY > 8);
  };
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });
}

/* ---------- Staggered reveal delays ---------- */
document.querySelectorAll("[data-stagger]").forEach((group) => {
  const items = group.matches(".fade-in")
    ? [group]
    : Array.from(group.children).filter((child) =>
        child.classList.contains("fade-in")
      );
  const targets = items.length
    ? items
    : Array.from(group.children);
  targets.forEach((item, index) => {
    item.style.setProperty("--reveal-delay", `${Math.min(index * 80, 480)}ms`);
  });
});

/* ---------- Scroll reveal ---------- */
const revealItems = document.querySelectorAll(".fade-in");

if (!prefersReducedMotion && "IntersectionObserver" in window && revealItems.length > 0) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.16, rootMargin: "0px 0px -8% 0px" }
  );

  revealItems.forEach((item) => observer.observe(item));
} else {
  revealItems.forEach((item) => item.classList.add("is-visible"));
}

/* ---------- Subtle hero parallax ---------- */
const heroVisual = document.querySelector(".hero-visual .axiom");

if (heroVisual && !prefersReducedMotion) {
  const hero = document.querySelector(".hero");
  let ticking = false;

  const update = () => {
    const offset = window.scrollY;
    if (offset < window.innerHeight) {
      heroVisual.style.transform = `translateY(${offset * 0.06}px)`;
    }
    ticking = false;
  };

  window.addEventListener(
    "scroll",
    () => {
      if (!ticking) {
        window.requestAnimationFrame(update);
        ticking = true;
      }
    },
    { passive: true }
  );
}
