const navToggle = document.querySelector("[data-nav-toggle]");
const navMenu = document.querySelector("[data-nav]");
const navDropdowns = document.querySelectorAll("[data-nav-dropdown]");

if (navMenu) {
  const currentPath = window.location.pathname;
  const currentFile = currentPath.endsWith("/") ? "index.html" : currentPath.split("/").pop();
  const navLinks = navMenu.querySelectorAll(".nav-links a");

  navLinks.forEach((link) => {
    const linkFile = new URL(link.getAttribute("href"), window.location.href).pathname.split("/").pop() || "index.html";
    const isCurrent = linkFile === currentFile;

    link.classList.toggle("is-active", isCurrent);

    if (isCurrent) {
      link.setAttribute("aria-current", "page");

      const parentDropdown = link.closest("[data-nav-dropdown]");

      if (parentDropdown) {
        const parentToggle = parentDropdown.querySelector(".nav-dropdown-toggle");

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

const revealItems = document.querySelectorAll(".fade-in");

if ("IntersectionObserver" in window && revealItems.length > 0) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.18 }
  );

  revealItems.forEach((item) => observer.observe(item));
} else {
  revealItems.forEach((item) => item.classList.add("is-visible"));
}
