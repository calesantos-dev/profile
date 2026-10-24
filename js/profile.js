const toggle = document.querySelector(".menu-toggle");
const navigation = document.querySelector("#navigation");
const languages = document.querySelector(".language-switch");
function closeMenu() {
  toggle.setAttribute("aria-expanded", "false");
  navigation.classList.remove("open");
}
toggle.addEventListener("click", () => {
  const open = toggle.getAttribute("aria-expanded") !== "true";
  toggle.setAttribute("aria-expanded", String(open));
  navigation.classList.toggle("open", open);
  if (open && languages) languages.open = false;
});
navigation.addEventListener("click", (event) => {
  if (event.target.closest("a")) closeMenu();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && languages?.open) {
    languages.open = false;
    languages.querySelector("summary").focus();
  }
  if (
    event.key === "Escape" &&
    toggle.getAttribute("aria-expanded") === "true"
  ) {
    closeMenu();
    toggle.focus();
  }
});
document.addEventListener("click", (event) => {
  if (!event.target.closest(".header")) closeMenu();
  if (languages && !event.target.closest(".language-switch")) languages.open = false;
});
languages?.addEventListener("toggle", () => {
  if (!languages.open) return;
  closeMenu();
  languages.querySelectorAll("a").forEach((link) => {
    const destination = new URL(link.href);
    destination.hash = window.location.hash;
    link.href = destination.href;
  });
});
window.matchMedia("(min-width: 1101px)").addEventListener("change", closeMenu);
document.querySelector("#year").textContent = new Date().getFullYear();

const clients = document.querySelector(".client-marquee");
const motionButton = document.querySelector(".client-motion");
if (clients && motionButton) {
  const list = clients.querySelector(".client-list");
  const copy = list.cloneNode(true);
  copy.classList.add("client-list-copy");
  copy.setAttribute("aria-hidden", "true");
  copy.removeAttribute("aria-label");
  clients.querySelector(".client-track").append(copy);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  function syncClientMotion() {
    clients.classList.toggle("is-animated", !reducedMotion.matches);
    motionButton.hidden = reducedMotion.matches;
  }
  motionButton.addEventListener("click", () => {
    const paused = motionButton.getAttribute("aria-pressed") !== "true";
    motionButton.setAttribute("aria-pressed", String(paused));
    clients.classList.toggle("is-paused", paused);
  });
  reducedMotion.addEventListener("change", syncClientMotion);
  syncClientMotion();
}
