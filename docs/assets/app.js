const DATA_URL = "data/projects.json";
const CLAY_TEXTURE_PATH = "./assets/clay_animation/clay0001.png";
const CLAY_TEXTURE_HOVER_PATH = "./assets/clay_animation/clay_animation_10fps.webp";
const CARD_BACKGROUND_GRADIENT = "linear-gradient(rgba(255, 255, 255, 0.24), rgba(255, 255, 255, 0.24))";

function enhanceCardClayAnimation() {
  const cards = document.querySelectorAll(".project-card, .film-card");
  if (!cards.length) return;

  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const applyTexture = (card, path) => {
    card.style.backgroundImage = `${CARD_BACKGROUND_GRADIENT}, url("${path}")`;
    card.style.backgroundRepeat = "repeat";
    card.style.backgroundSize = "420px 420px";
    card.style.backgroundBlendMode = "normal, normal";
  };

  cards.forEach((card) => {
    applyTexture(card, CLAY_TEXTURE_PATH);
    if (prefersReducedMotion) return;

    card.addEventListener("mouseenter", () => applyTexture(card, CLAY_TEXTURE_HOVER_PATH));
    card.addEventListener("mouseleave", () => applyTexture(card, CLAY_TEXTURE_PATH));
    card.addEventListener("focusin", () => applyTexture(card, CLAY_TEXTURE_HOVER_PATH));
    card.addEventListener("focusout", () => applyTexture(card, CLAY_TEXTURE_PATH));
  });
}

function getQueryParam(name) {
  const url = new URL(window.location.href);
  return url.searchParams.get(name) || "";
}

function safeText(value) {
  return (value || "").toString();
}

function isFileProtocol() {
  return window.location.protocol === "file:";
}

function escapeAttr(value) {
  return safeText(value)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function isVideo(path) {
  return /\.(mp4|webm|mov|m4v|avi|mkv)$/i.test(path || "");
}

function choosePreview(project) {
  if (project.assets.preview) return project.assets.preview;
  if (project.assets.thumbnail) return project.assets.thumbnail;
  if (project.assets.poster) return project.assets.poster;
  return (project.assets.media && project.assets.media[0]) || "";
}

function buildTagList(tags) {
  if (!Array.isArray(tags) || tags.length === 0) return "";
  return `
    <ul class="tag-row">
      ${tags.map((tag) => `<li>${safeText(tag)}</li>`).join("")}
    </ul>
  `;
}

function externalLink(label, href, className = "btn") {
  if (!href) return "";
  return `<a class="${className}" href="${href}" target="_blank" rel="noopener noreferrer">${label}</a>`;
}

function videoFallbackMarkup(path, label = "Open video") {
  const href = escapeAttr(path || "");
  return `<div class="media-placeholder">Video unavailable in this browser. ${href ? `<a href="${href}" target="_blank" rel="noopener noreferrer">${label}</a>` : ""}</div>`;
}

function videoOnErrorHandler(path) {
  const encoded = encodeURIComponent(videoFallbackMarkup(path));
  return `this.outerHTML=decodeURIComponent('${encoded}')`;
}

function setVideoWrapAspectRatio(video) {
  const wrap = video?.closest?.(".video-wrap");
  if (!wrap || !video?.videoWidth || !video?.videoHeight) return;
  wrap.style.setProperty("--video-aspect-ratio", `${video.videoWidth} / ${video.videoHeight}`);
}

function youtubeEmbedMarkup(project, title) {
  const embedUrl = project?.links?.youtubeEmbed || "";
  const youtubeUrl = project?.links?.youtube || "";
  if (!embedUrl) return "";

  if (isFileProtocol()) {
    return `
      <div class="video-wrap video-fallback">
        <p>Embedded YouTube playback is unavailable when this page is opened directly from disk.</p>
        ${youtubeUrl ? `<a class="btn" href="${escapeAttr(youtubeUrl)}" target="_blank" rel="noopener noreferrer">Watch on YouTube</a>` : ""}
      </div>
    `;
  }

  return `
    <div class="video-wrap"><iframe src="${escapeAttr(embedUrl)}" title="${escapeAttr(title)} trailer" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></div>
  `;
}

function projectPrimaryMediaMarkup(project, title) {
  const media = Array.isArray(project?.assets?.media) ? project.assets.media : [];
  const localVideo = media.find((path) => isVideo(path)) || "";
  const youtubeUrl = project?.links?.youtube || "";

  if (localVideo) {
    const href = escapeAttr(localVideo);
    return {
      primaryMarkup: `
        <div class="video-wrap"><video controls playsinline preload="metadata" src="${href}" onloadedmetadata="setVideoWrapAspectRatio(this)" onerror="${videoOnErrorHandler(localVideo)}"></video></div>
        ${youtubeUrl ? `<div class="project-media-actions">${externalLink("Watch on YouTube", youtubeUrl, "btn")}</div>` : ""}
      `,
      usedLocalVideo: localVideo,
    };
  }

  return {
    primaryMarkup: youtubeEmbedMarkup(project, title),
    usedLocalVideo: "",
  };
}

function renderMedia(path, alt, className = "media-thumb") {
  if (!path) return `<div class="media-placeholder">No preview</div>`;
  if (isVideo(path)) {
    const href = escapeAttr(path);
    return `<video class="${className}" src="${href}" autoplay loop muted playsinline preload="metadata" onerror="${videoOnErrorHandler(path)}"></video>`;
  }
  // Image case – click opens lightbox
  const href = escapeAttr(path);
  const safeAlt = escapeAttr(alt);
  return `<img class="${className}" src="${href}" alt="${safeAlt}" loading="lazy" onclick="openLightbox('${href}', '${safeAlt}')" style="cursor:pointer;" />`;
}

// Lightbox helper functions
function ensureLightbox() {
  if (document.getElementById('lightbox')) return;
  const lightbox = document.createElement('div');
  lightbox.id = 'lightbox';
  lightbox.className = 'lightbox hidden';
  lightbox.innerHTML = `
    <div class="lightbox-content">
      <button class="lightbox-close" aria-label="Close">✕</button>
      <img class="lightbox-img" src="" alt="" />
    </div>`;
  document.body.appendChild(lightbox);
  const closeBtn = lightbox.querySelector('.lightbox-close');
  closeBtn.addEventListener('click', closeLightbox);
  lightbox.addEventListener('click', (e) => { if (e.target === lightbox) closeLightbox(); });
}
function openLightbox(src, alt) {
  const lightbox = document.getElementById('lightbox');
  const img = lightbox.querySelector('.lightbox-img');
  img.src = src;
  img.alt = alt || '';
  lightbox.classList.add('visible');
}
function closeLightbox() {
  const lightbox = document.getElementById('lightbox');
  lightbox.classList.remove('visible');
}

document.addEventListener('DOMContentLoaded', ensureLightbox);

function projectCard(project) {
  const preview = choosePreview(project);
  const title = safeText(project.title);
  const desc = safeText(project.description);

  if (project.type === "coding") {
    const href = project.links.git || project.links.github || "#";
    const disabledClass = href !== "#" ? "" : " disabled";
    return `
      <article class="project-card${disabledClass}">
        <a class="card-link" ${href !== "#" ? `href="${href}" target="_blank" rel="noopener noreferrer"` : ""}>
          ${renderMedia(preview, `${title} thumbnail`)}
          <div class="card-content">
            <h3>${title}</h3>
            <p>${desc}</p>
          </div>
        </a>
      </article>
    `;
  }

  const href = `project.html?slug=${encodeURIComponent(project.slug)}`;

  return `
    <article class="project-card">
      <a class="card-link" href="${href}">
        ${renderMedia(preview, `${title} preview`)}
        <div class="card-content">
          <h3>${title}</h3>
          <p>${desc}</p>
        </div>
      </a>
    </article>
  `;
}

function filmCard(project) {
  const title = safeText(project.title);
  const poster = project.assets.poster || project.assets.thumbnail || choosePreview(project);
  const trailer = youtubeEmbedMarkup(project, `${title} trailer`);

  return `
    <article class="film-card">
      <div class="film-card-top">
        ${renderMedia(poster, `${title} poster`, "film-poster")}
        <div>
          <h3>${title}</h3>
          <p>${safeText(project.description)}</p>
          ${buildTagList(project.tags)}
          ${trailer}
        </div>
      </div>
    </article>
  `;
}

function emptyState(message) {
  return `<p class="empty-state">${message}</p>`;
}

async function loadData() {
  const response = await fetch(DATA_URL, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Unable to load project data. Run build_portfolio_site.py first.");
  }
  return response.json();
}

function renderHero(bio) {
  const hero = document.getElementById("hero");
  if (!hero) return;

  const links = bio.links || {};
  hero.innerHTML = `
    <div class="hero-copy reveal">
      <p class="eyebrow">Creative Technologist</p>
      <h1>${safeText(bio.name || "Portfolio")}</h1>
      <p class="hero-text">${safeText(bio.bio || "")}</p>
      <div class="button-row">
        ${externalLink("Resume", bio.resume, "btn btn-primary")}
        ${externalLink("Demo Reel", links.demoReel, "btn btn-primary")}
        ${externalLink("GitHub", links.github, "btn")}
        ${externalLink("YouTube", links.youtube, "btn")}
        ${externalLink("LinkedIn", "https://www.linkedin.com/in/cole-stevenson-47755b158/", "btn")}
      </div>
    </div>
    <div class="hero-image reveal">
      ${bio.headshot ? `<img src="${bio.headshot}" alt="${safeText(bio.name)} headshot" />` : ""}
    </div>
  `;
}

function renderHome(data) {
  renderHero(data.bio || {});

  const featured = (data.projects || []).filter((project) => Boolean(project.featured));
  const film = featured.filter((project) => project.type === "film");
  const art = featured.filter((project) => project.type === "art");
  const coding = featured.filter((project) => project.type === "coding");

  const filmGrid = document.getElementById("film-grid");
  const artGrid = document.getElementById("art-grid");
  const codingGrid = document.getElementById("coding-grid");

  if (filmGrid) {
    filmGrid.innerHTML = film.length ? film.map(filmCard).join("") : emptyState("No featured film projects yet.");
  }

  if (artGrid) {
    artGrid.innerHTML = art.length ? art.map(projectCard).join("") : emptyState("No featured art projects yet.");
  }

  if (codingGrid) {
    codingGrid.innerHTML = coding.length ? coding.map(projectCard).join("") : emptyState("No featured coding projects yet.");
  }
}

function renderSection(data) {
  const type = (getQueryParam("type") || "").toLowerCase();
  const title = document.getElementById("section-title");
  const grid = document.getElementById("section-grid");

  if (!grid || !title) return;

  if (!["film", "art", "coding"].includes(type)) {
    title.textContent = "Projects";
    grid.innerHTML = emptyState("Choose a valid section from the home page.");
    return;
  }

  title.textContent = `${type[0].toUpperCase()}${type.slice(1)} Projects`;
  const projects = (data.projects || []).filter((project) => project.type === type);

  if (projects.length === 0) {
    grid.innerHTML = emptyState(`No ${type} projects found.`);
    return;
  }

  if (type === "film") {
    grid.classList.add("film-grid");
    grid.innerHTML = projects.map(filmCard).join("");
    return;
  }

  grid.innerHTML = projects.map(projectCard).join("");
}

function renderProjectPage(data) {
  const slug = getQueryParam("slug");
  const project = (data.projects || []).find((item) => item.slug === slug);
  const container = document.getElementById("project-main");
  const back = document.getElementById("back-to-section");

  if (!container) return;

  if (!project) {
    container.innerHTML = emptyState("Project not found.");
    return;
  }

  if (back) {
    back.setAttribute("href", `section.html?type=${encodeURIComponent(project.type)}`);
  }

  const { primaryMarkup, usedLocalVideo } = projectPrimaryMediaMarkup(project, `${safeText(project.title)} video`);
  let skippedPrimaryVideo = false;

  const media = (project.assets.media || [])
    .filter((path) => {
      if (usedLocalVideo && !skippedPrimaryVideo && path === usedLocalVideo) {
        skippedPrimaryVideo = true;
        return false;
      }
      return true;
    })
    .map((path) => {
    if (isVideo(path)) {
      const href = escapeAttr(path);
      return `<video controls playsinline preload="metadata" src="${href}" onloadedmetadata="setVideoWrapAspectRatio(this)" onerror="${videoOnErrorHandler(path)}"></video>`;
    }
    return `<img src="${escapeAttr(path)}" alt="${escapeAttr(safeText(project.title))} media" loading="lazy" />`;
  });

  container.innerHTML = `
    <article class="project-detail reveal">
      <h1>${safeText(project.title)}</h1>
      <p class="detail-description">${safeText(project.description)}</p>
      ${buildTagList(project.tags)}
      ${primaryMarkup}
      ${media.length ? `<section class="detail-gallery">${media.join("")}</section>` : ""}
    </article>
  `;
}

function runRevealAnimation() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("in-view");
      }
    });
  }, { threshold: 0.2 });

  document.querySelectorAll(".reveal, .project-card, .film-card").forEach((element) => {
    observer.observe(element);
  });
}

async function main() {
  try {
    const data = await loadData();
    const page = document.body.dataset.page;

    if (page === "home") {
      renderHome(data);
    } else if (page === "section") {
      renderSection(data);
    } else if (page === "project") {
      renderProjectPage(data);
    }

    enhanceCardClayAnimation();
    runRevealAnimation();
  } catch (error) {
    const root = document.querySelector("main");
    if (root) {
      root.innerHTML = `<p class="empty-state">${safeText(error.message)}</p>`;
    }
  }
}

main();