<script setup>
import { RouterLink } from 'vue-router'
</script>

<template>
  <section class="not-found-page">
    <div class="not-found-card soft-acrylic">
      <p class="eyebrow">404</p>
      <h1>Page not found</h1>
      <p>The route you opened does not exist in this MVP.</p>
      <RouterLink class="primary-button" to="/">Return Home</RouterLink>
    </div>
  </section>
</template>

