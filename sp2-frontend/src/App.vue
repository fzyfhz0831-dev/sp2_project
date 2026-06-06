<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="app-shell">
    <header class="site-navbar">
      <div class="nav-inner soft-acrylic">
        <RouterLink class="brand" to="/" aria-label="SpireInsight home">
          <span class="brand-mark">SI</span>
          <span>SpireInsight</span>
        </RouterLink>

        <nav class="nav-links" aria-label="Primary navigation">
          <RouterLink to="/" class="nav-link">Tool</RouterLink>
          <RouterLink to="/json-guide" class="nav-link">JSON Guide</RouterLink>
        </nav>

        <RouterLink class="nav-action" to="/#analysis">Analyze Run</RouterLink>
      </div>
    </header>

    <main class="site-main">
      <RouterView />
    </main>

    <footer class="site-footer">
      <span>SpireInsight</span>
      <span class="footer-dot">·</span>
      <span>AI-powered Slay the Spire diagnostics</span>
      <br />
      <span>© 2026 KaiSa Feng</span>
    </footer>
  </div>
</template>

