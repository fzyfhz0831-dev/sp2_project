<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import insightArt from '../assets/insight-stack.png'
import { analyzeRunFile } from '../services/insightsApi'

const router = useRouter()

const ANALYSIS_SECTIONS = [
  'Reason for success/failure',
  '3 key mistakes',
  '3 improvement suggestions',
  'Short summary',
]

// Hardcoded defaults — used while run_options.json loads and as fallback.
const DEFAULT_CHARACTERS = [
  { value: 'ironclad', label: 'The Ironclad' },
  { value: 'silent', label: 'The Silent' },
  { value: 'defect', label: 'The Defect' },
  { value: 'watcher', label: 'The Watcher' },
]

const DEFAULT_LOCATIONS = [
  { value: 'act_1_elite', label: 'Act 1 Elite' },
  { value: 'act_1_boss', label: 'Act 1 Boss' },
  { value: 'act_2_elite', label: 'Act 2 Elite' },
  { value: 'act_2_boss', label: 'Act 2 Boss' },
  { value: 'act_3_elite', label: 'Act 3 Elite' },
  { value: 'act_3_boss', label: 'Act 3 Boss' },
  { value: 'heart', label: 'The Heart' },
  { value: 'hallway', label: 'Hallway Fight' },
]

const DEFAULT_PROBLEMS = [
  { value: 'low_block', label: 'Low Block' },
  { value: 'low_damage', label: 'Low Damage' },
  { value: 'poor_scaling', label: 'Poor Scaling' },
  { value: 'bad_draw', label: 'Bad Card Draw' },
  { value: 'high_cost_deck', label: 'High-Cost Deck' },
  { value: 'risky_pathing', label: 'Risky Pathing' },
  { value: 'deck_bloat', label: 'Deck Bloat' },
  { value: 'relic_mismatch', label: 'Relic Mismatch' },
]

const characters = ref([...DEFAULT_CHARACTERS])
const locations = ref([...DEFAULT_LOCATIONS])
const problems = ref([...DEFAULT_PROBLEMS])
const optionsLoadError = ref('')

const selectedCharacter = ref('')
const selectedLocation = ref('')
const selectedProblem = ref('')
const selectedJsonFile = ref(null)
const result = ref(null)
const isAnalyzing = ref(false)
const uploadStatus = ref('Choose a run JSON file to analyze.')
const errorMessage = ref('')

onMounted(async () => {
  try {
    const resp = await fetch('/data/run_options.json')
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    if (Array.isArray(data.characters) && data.characters.length) {
      characters.value = data.characters
    }
    if (Array.isArray(data.deathLocations) && data.deathLocations.length) {
      locations.value = data.deathLocations
    }
    if (Array.isArray(data.mainProblems) && data.mainProblems.length) {
      problems.value = data.mainProblems
    }
  } catch (err) {
    // Use defaults on any error — the app still works.
    optionsLoadError.value = err instanceof Error ? err.message : 'Unknown error'
  }
})

const selectedRun = computed(() => ({
  character: selectedCharacter.value,
  location: selectedLocation.value,
  problem: selectedProblem.value,
}))

const canAnalyze = computed(() => Boolean(selectedJsonFile.value))

const runLabel = computed(() => [
  result.value?.filename,
  findOptionLabel(characters, selectedRun.value.character),
  findOptionLabel(locations, selectedRun.value.location),
  findOptionLabel(problems, selectedRun.value.problem),
].filter(Boolean).join(' / '))

function findOptionLabel(options, value) {
  return options.find((item) => item.value === value)?.label
}

function onFileChange(event) {
  const [file] = event.target.files || []
  selectedJsonFile.value = file || null

  result.value = null
  errorMessage.value = ''
  uploadStatus.value = file
    ? `${file.name} selected.`
    : 'Choose a run JSON file to analyze.'
}

function normalizeHeading(line) {
  return line
    .trim()
    .replace(/^\d+\.\s*/, '')
    .replace(/:$/, '')
}

function splitAnalysisSections(analysis) {
  const sections = []
  let currentSection = null

  for (const line of String(analysis || '').split(/\r?\n/)) {
    const heading = normalizeHeading(line)
    const label = ANALYSIS_SECTIONS.find(
      (sectionLabel) => sectionLabel.toLowerCase() === heading.toLowerCase(),
    )

    if (label) {
      currentSection = { label, textLines: [] }
      sections.push(currentSection)
      continue
    }

    if (currentSection) {
      currentSection.textLines.push(line)
    }
  }

  const formattedSections = sections.map((section) => ({
    label: section.label,
    text: section.textLines.join('\n').trim(),
  })).filter((section) => section.text)

  if (formattedSections.length > 0) {
    return formattedSections
  }

  return [{ label: 'Analysis', text: String(analysis || 'No analysis text returned.') }]
}

function formatResultValue(value, fallback = 'Not returned') {
  if (value === null || value === undefined || value === '') {
    return fallback
  }

  if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  }

  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2)
  }

  return String(value)
}

function formatBackendResult(response) {
  const error = response.error || response.detail || ''

  // Extract structured findings from the response.
  const findings = response.findings || null

  return {
    title: response.success ? 'Analysis complete' : 'Analysis result',
    raw: response,
    success: response.success === true,
    filename: response.filename || selectedJsonFile.value?.name || 'Uploaded run',
    runId: response.run_id,
    summaryText: response.summary_text || '',
    analysis: response.analysis || '',
    error,
    sections: splitAnalysisSections(response.analysis),
    findings,
  }
}

function hasFindings(findings) {
  if (!findings) return false
  return (
    (findings.problems && findings.problems.length > 0) ||
    (findings.strengths && findings.strengths.length > 0) ||
    (findings.warnings && findings.warnings.length > 0) ||
    (findings.suggestions && findings.suggestions.length > 0)
  )
}

async function analyzeRun() {
  if (!canAnalyze.value) return

  const file = selectedJsonFile.value
  isAnalyzing.value = true
  errorMessage.value = ''
  result.value = null
  uploadStatus.value = 'Analyzing...'

  try {
    const response = await analyzeRunFile(file, {
      character: selectedCharacter.value || undefined,
      deathLocation: selectedLocation.value || undefined,
      mainProblem: selectedProblem.value || undefined,
    })
    result.value = formatBackendResult(response)
    uploadStatus.value = `Analysis complete for ${result.value.filename}.`
  } catch (error) {
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Could not analyze the uploaded run.'
    uploadStatus.value = 'Upload failed.'
  } finally {
    isAnalyzing.value = false
  }
}

function openJsonGuide() {
  router.push('/json-guide')
}
</script>

<template>
  <div class="home-page">
    <section id="analysis" class="hero-tool">
      <div class="hero-copy">
        <p class="eyebrow">SpireInsight</p>
        <h1>Why Did I Die?</h1>
        <p class="hero-lede">
          Turn a failed Slay the Spire run into a clear next-step diagnosis.
        </p>
        <div class="signal-row" aria-label="Analysis focus areas">
          <span>Damage</span>
          <span>Block</span>
          <span>Scaling</span>
          <span>Draw</span>
        </div>
        <div class="insight-visual" aria-hidden="true">
          <img :src="insightArt" alt="" />
          <div>
            <span>Run readout</span>
            <strong>4 checkpoints scanned</strong>
          </div>
        </div>
      </div>

      <form class="tool-panel soft-acrylic" @submit.prevent="analyzeRun">
        <div class="panel-heading">
          <p class="eyebrow">Run Analysis</p>
          <h2>Upload a run JSON</h2>
          <p>Upload the run data JSON file from your Slay the Spire 2 runs folder for an AI-powered diagnosis.</p>
        </div>

        <div class="field-grid">
          <label class="field field-wide">
            <span>Run JSON</span>
            <div class="file-input-row">
              <input
                class="file-control"
                type="file"
                accept=".json,application/json"
                @change="onFileChange"
              />
              <button type="button" class="guide-button" @click="openJsonGuide">
                <span class="guide-icon" aria-hidden="true">?</span>
                <span>JSON Guide</span>
              </button>
            </div>
          </label>

          <label class="field">
            <span>Character</span>
            <select v-model="selectedCharacter" class="select-control">
              <option value="" disabled>Select character</option>
              <option v-for="character in characters" :key="character.value" :value="character.value">
                {{ character.label }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>Death Location</span>
            <select v-model="selectedLocation" class="select-control">
              <option value="" disabled>Select location</option>
              <option v-for="location in locations" :key="location.value" :value="location.value">
                {{ location.label }}
              </option>
            </select>
          </label>

          <label class="field field-wide">
            <span>Main Problem</span>
            <select v-model="selectedProblem" class="select-control">
              <option value="" disabled>Select problem</option>
              <option v-for="problem in problems" :key="problem.value" :value="problem.value">
                {{ problem.label }}
              </option>
            </select>
          </label>
        </div>

        <p v-if="errorMessage" class="form-message form-error">{{ errorMessage }}</p>
        <p v-else class="form-message">{{ uploadStatus }}</p>

        <button class="primary-button" type="submit" :disabled="!canAnalyze || isAnalyzing">
          <span>{{ isAnalyzing ? 'Analyzing...' : 'Upload & Analyze' }}</span>
          <span aria-hidden="true">&gt;</span>
        </button>
      </form>
    </section>

    <section class="result-section" aria-live="polite">
      <div v-if="result" class="result-layout">
        <article class="result-summary soft-acrylic">
          <p class="eyebrow">Diagnostic Result</p>
          <h2>{{ result.title }}</h2>
          <div class="result-status-row">
            <span>success</span>
            <strong>{{ formatResultValue(result.success) }}</strong>
          </div>
          <p>{{ result.summaryText || runLabel }}</p>
          <div class="confidence">
            <span>Run ID</span>
            <strong>{{ result.runId ? `#${result.runId}` : 'Saved' }}</strong>
          </div>
        </article>

        <div class="result-cards">
          <article v-for="section in result.sections" :key="section.label" class="result-card">
            <span>{{ section.label }}</span>
            <p>{{ section.text }}</p>
          </article>
        </div>

        <div v-if="hasFindings(result.findings)" class="findings-section">
          <div v-if="result.findings.run_context" class="run-context-bar soft-acrylic">
            <div class="context-item">
              <span>Character</span>
              <strong>{{ result.findings.run_context.character }}</strong>
            </div>
            <div class="context-item">
              <span>Floor</span>
              <strong>{{ result.findings.run_context.floor }}</strong>
            </div>
            <div class="context-item">
              <span>Boss</span>
              <strong>{{ result.findings.run_context.boss }}</strong>
            </div>
            <div class="context-item">
              <span>Deck Size</span>
              <strong>{{ result.findings.run_context.deck_size }}</strong>
            </div>
            <div class="context-item">
              <span>Relics</span>
              <strong>{{ result.findings.run_context.relic_count }}</strong>
            </div>
            <div class="context-item" v-if="result.findings.run_context.victory !== null">
              <span>Result</span>
              <strong :class="result.findings.run_context.victory ? 'text-green' : 'text-red'">
                {{ result.findings.run_context.victory ? 'Victory' : 'Defeat' }}
              </strong>
            </div>
          </div>

          <div class="findings-grid">
          <article v-if="result.findings.problems.length" class="finding-card finding-problems">
            <span class="finding-badge finding-badge-problems">Problems</span>
            <ul>
              <li v-for="(item, i) in result.findings.problems" :key="'p-'+i">{{ item }}</li>
            </ul>
          </article>

          <article v-if="result.findings.strengths.length" class="finding-card finding-strengths">
            <span class="finding-badge finding-badge-strengths">Strengths</span>
            <ul>
              <li v-for="(item, i) in result.findings.strengths" :key="'s-'+i">{{ item }}</li>
            </ul>
          </article>

          <article v-if="result.findings.warnings.length" class="finding-card finding-warnings">
            <span class="finding-badge finding-badge-warnings">Warnings</span>
            <ul>
              <li v-for="(item, i) in result.findings.warnings" :key="'w-'+i">{{ item }}</li>
            </ul>
          </article>

          <article v-if="result.findings.suggestions.length" class="finding-card finding-suggestions">
            <span class="finding-badge finding-badge-suggestions">Suggestions</span>
            <ul>
              <li v-for="(item, i) in result.findings.suggestions" :key="'sg-'+i">{{ item }}</li>
            </ul>
          </article>
        </div>
        </div>

        <article class="metrics-card soft-acrylic">
          <div class="metrics-heading">
            <p class="eyebrow">Backend Result</p>
            <h2>{{ result.filename }}</h2>
          </div>
          <dl class="backend-fields">
            <div>
              <dt>success</dt>
              <dd>{{ formatResultValue(result.raw.success) }}</dd>
            </div>
            <div>
              <dt>summary_text</dt>
              <dd>{{ formatResultValue(result.raw.summary_text, 'No summary_text returned.') }}</dd>
            </div>
            <div v-if="result.error">
              <dt>error</dt>
              <dd>{{ formatResultValue(result.error) }}</dd>
            </div>
          </dl>
          <div class="analysis-block">
            <span>analysis</span>
            <pre class="analysis-text">{{ formatResultValue(result.raw.analysis, 'No analysis returned.') }}</pre>
          </div>
        </article>
      </div>

      <div v-else-if="errorMessage" class="empty-state result-error-state soft-acrylic">
        <p class="eyebrow">Analysis Error</p>
        <h2>Upload failed</h2>
        <p>{{ errorMessage }}</p>
      </div>

      <div v-else class="empty-state soft-acrylic">
        <p class="eyebrow">Ready when you are</p>
        <h2>No run analyzed yet</h2>
        <p>Upload a run JSON file from your Slay the Spire 2 runs folder to get started.</p>
      </div>
    </section>
  </div>
</template>

