<script setup>
import { RouterLink } from 'vue-router'
import step1Img from '../assets/json-guide/step1-steam-library.jpg'
import step2Img from '../assets/json-guide/step2-browse-local-files.jpg'
import step3Img from '../assets/json-guide/step3-runs-folder.jpg'

const steps = [
  {
    num: 1,
    title: 'Step 1: Open Steam Library and select Slay the Spire 2.',
    detail:
      'Launch Steam, open your Library, then click Slay the Spire 2 in the game list.',
    img: step1Img,
    alt: 'Steam Library showing Slay the Spire 2 selected in the game list',
  },
  {
    num: 2,
    title: 'Step 2: Click gear icon → Manage → Browse Local Files.',
    detail:
      'On the game page, click the gear icon near the Play button. Choose Manage, then Browse Local Files to open the install folder.',
    img: step2Img,
    alt: 'Steam game page showing the gear icon menu with Manage and Browse Local Files',
  },
  {
    num: 3,
    title: 'Step 3: Search/open the runs folder.',
    detail:
      'In File Explorer, open the runs folder. If you do not see it immediately, use the search box in the game folder and search for runs.',
    img: step3Img,
    alt: 'File Explorer showing the runs folder and recent JSON run files',
  },
  {
    num: 4,
    title: 'Step 4: Upload the newest .json file to Run Doctor.',
    detail:
      'Pick the newest .json run file, return to Run Doctor, and upload it with the Run JSON input.',
    img: null,
    alt: '',
  },
]
</script>

<template>
  <section class="json-guide-page">
    <div class="page-heading">
      <p class="eyebrow">JSON Guide · How to Find Run JSON</p>
      <h1>Locate your run data file</h1>
      <p>
        Follow these four steps to find your newest run JSON, then upload it to
        Run Doctor for analysis.
      </p>
    </div>

    <div class="guide-steps">
      <article
        v-for="step in steps"
        :key="step.num"
        class="guide-step-card soft-acrylic"
      >
        <div class="step-number">
          <span>{{ step.num }}</span>
        </div>
        <div class="step-body">
          <h2>{{ step.title }}</h2>
          <p>{{ step.detail }}</p>
          <img
            v-if="step.img"
            :src="step.img"
            :alt="step.alt"
            class="step-screenshot"
            loading="lazy"
          />
        </div>
      </article>
    </div>

    <div class="guide-fallback soft-acrylic">
      <div class="fallback-icon" aria-hidden="true">Tip</div>
      <div>
        <h3>Can't find the runs folder or JSON files?</h3>
        <p>
          Make sure you have launched Slay the Spire 2 and completed at least
          one run. If the folder is still missing, verify the game through
          Steam: Properties → Installed Files → Verify integrity.
        </p>
      </div>
    </div>

    <div class="guide-actions">
      <RouterLink class="primary-button" to="/#analysis">
        <span>Back to Run Doctor</span>
        <span aria-hidden="true">&gt;</span>
      </RouterLink>
    </div>
  </section>
</template>
