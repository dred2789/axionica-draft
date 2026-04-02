const navToggle = document.querySelector("[data-nav-toggle]");
const navMenu = document.querySelector("[data-nav]");
const navDropdowns = document.querySelectorAll("[data-nav-dropdown]");

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
