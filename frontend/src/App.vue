<script setup>
import { computed, onMounted, ref } from 'vue'

const views = [
  {
    id: 'unclaimed',
    label: 'Unclaimed',
    title: 'Unclaimed Tickets',
    endpoint: '/api/items',
    empty: 'No unclaimed tickets',
  },
  {
    id: 'mine',
    label: 'Claimed by me',
    title: 'Claimed by Me',
    endpoint: '/api/items/claimed-by-me',
    empty: 'No tickets claimed by you',
  },
]

const items = ref([])
const selectedId = ref(null)
const selectedView = ref('unclaimed')
const currentReviewer = ref('alex')
const unclaimedCount = ref(0)
const claimedByMeCount = ref(0)
const terminalCount = ref(0)
const loading = ref(true)
const acting = ref(false)
const pendingAction = ref('')
const error = ref('')
const feedback = ref('')

const currentView = computed(() => views.find((view) => view.id === selectedView.value) || views[0])
const selectedItem = computed(() => items.value.find((item) => item.id === selectedId.value) || null)
const unclaimedBadgeCount = computed(() =>
  selectedView.value === 'unclaimed' ? items.value.length : unclaimedCount.value,
)
const mineBadgeCount = computed(() =>
  selectedView.value === 'mine' ? items.value.length : claimedByMeCount.value,
)

const ageLabel = (submittedAt) => {
  const formatter = new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
  return formatter.format(new Date(submittedAt))
}

const actionLabel = (action) => {
  const labels = {
    claim: 'Claim',
    approve: 'Approve',
    reject: 'Reject',
    escalate: 'Escalate',
  }
  return labels[action] || action
}

async function loadQueue(preferredId = selectedId.value) {
  loading.value = true
  error.value = ''

  try {
    const response = await fetch(currentView.value.endpoint)
    if (!response.ok) {
      throw new Error('Queue could not be loaded')
    }

    const payload = await response.json()
    items.value = payload.items
    currentReviewer.value = payload.current_reviewer
    unclaimedCount.value = payload.unclaimed_count
    claimedByMeCount.value = payload.claimed_by_me_count
    terminalCount.value = payload.terminal_count

    const preferredStillActive = items.value.some((item) => item.id === preferredId)
    selectedId.value = preferredStillActive ? preferredId : items.value[0]?.id || null
  } catch (loadError) {
    error.value = loadError.message
  } finally {
    loading.value = false
  }
}

async function switchView(viewId) {
  if (selectedView.value === viewId || acting.value) return

  selectedView.value = viewId
  selectedId.value = null
  feedback.value = ''
  await loadQueue(null)
}

async function performAction(action) {
  if (!selectedItem.value || acting.value) return

  acting.value = true
  pendingAction.value = action
  error.value = ''
  feedback.value = ''

  try {
    const response = await fetch(`/api/items/${selectedItem.value.id}/actions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, reviewer: currentReviewer.value }),
    })
    const payload = await response.json()

    if (!response.ok) {
      throw new Error(payload.detail || 'Action was rejected')
    }

    feedback.value = payload.message
    const nextSelection = payload.item.allowed_actions.length > 0 ? payload.item.id : null
    await loadQueue(nextSelection)
  } catch (actionError) {
    error.value = actionError.message
  } finally {
    acting.value = false
    pendingAction.value = ''
  }
}

onMounted(() => loadQueue())
</script>

<template>
  <main class="workspace">
    <header class="topbar">
      <div>
        <p class="eyebrow">Reviewer workspace</p>
        <h1>{{ currentView.title }}</h1>
      </div>
      <dl class="metrics" aria-label="Queue summary">
        <div>
          <dt>Reviewer</dt>
          <dd>{{ currentReviewer }}</dd>
        </div>
        <div>
          <dt>Unclaimed</dt>
          <dd>{{ unclaimedCount }}</dd>
        </div>
        <div>
          <dt>Mine</dt>
          <dd>{{ claimedByMeCount }}</dd>
        </div>
        <div>
          <dt>Closed</dt>
          <dd>{{ terminalCount }}</dd>
        </div>
      </dl>
    </header>

    <nav class="view-switcher" aria-label="Queue views">
      <button
        v-for="view in views"
        :key="view.id"
        class="view-tab"
        :class="{ selected: selectedView === view.id }"
        type="button"
        :aria-current="selectedView === view.id ? 'page' : undefined"
        :disabled="acting"
        @click="switchView(view.id)"
      >
        <span>{{ view.label }}</span>
        <strong>{{ view.id === 'unclaimed' ? unclaimedBadgeCount : mineBadgeCount }}</strong>
      </button>
    </nav>

    <p v-if="feedback" class="feedback" role="status">{{ feedback }}</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <div v-if="loading" class="loading">Loading queue...</div>

    <section v-else class="layout" aria-label="Reviewer queue workspace">
      <aside class="queue" :aria-label="currentView.title">
        <button
          v-for="item in items"
          :key="item.id"
          class="queue-item"
          :class="{ selected: item.id === selectedId }"
          type="button"
          @click="selectedId = item.id"
        >
          <span class="rank">#{{ item.urgency_rank }}</span>
          <span class="item-main">
            <strong>{{ item.title }}</strong>
            <span>{{ item.id }} · {{ ageLabel(item.submitted_at) }}</span>
          </span>
          <span class="tags">
            <span class="tag" :class="item.risk_level">{{ item.risk_level }}</span>
            <span class="tag tier">{{ item.customer_tier }}</span>
          </span>
        </button>

        <p v-if="items.length === 0" class="empty">{{ currentView.empty }}</p>
      </aside>

      <article v-if="selectedItem" class="detail">
        <div class="detail-heading">
          <div>
            <p class="eyebrow">{{ selectedItem.id }}</p>
            <h2>{{ selectedItem.title }}</h2>
          </div>
          <span class="status">{{ selectedItem.status.replace('_', ' ') }}</span>
        </div>

        <p class="summary">{{ selectedItem.summary }}</p>

        <dl class="facts">
          <div>
            <dt>Submitted</dt>
            <dd>{{ ageLabel(selectedItem.submitted_at) }}</dd>
          </div>
          <div>
            <dt>Risk</dt>
            <dd>{{ selectedItem.risk_level }}</dd>
          </div>
          <div>
            <dt>Customer</dt>
            <dd>{{ selectedItem.customer_tier }}</dd>
          </div>
          <div>
            <dt>Assigned</dt>
            <dd>{{ selectedItem.assigned_reviewer || 'Unassigned' }}</dd>
          </div>
          <div>
            <dt>Notes</dt>
            <dd>{{ selectedItem.notes_count }}</dd>
          </div>
        </dl>

        <div class="actions" aria-label="Workflow actions">
          <button
            v-for="action in selectedItem.allowed_actions"
            :key="action"
            class="action"
            :class="action"
            type="button"
            :disabled="acting"
            @click="performAction(action)"
          >
            {{ pendingAction === action ? 'Working...' : actionLabel(action) }}
          </button>
          <span v-if="selectedItem.allowed_actions.length === 0" class="no-actions">
            No further actions
          </span>
        </div>
      </article>

      <article v-else class="detail empty-detail">
        <h2>{{ currentView.empty }}</h2>
      </article>
    </section>
  </main>
</template>
