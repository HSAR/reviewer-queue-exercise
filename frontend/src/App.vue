<script setup>
import { computed, onMounted, ref } from 'vue'

const items = ref([])
const selectedId = ref(null)
const currentReviewer = ref('alex')
const activeCount = ref(0)
const terminalCount = ref(0)
const loading = ref(true)
const acting = ref(false)
const pendingAction = ref('')
const error = ref('')
const feedback = ref('')

const selectedItem = computed(() => items.value.find((item) => item.id === selectedId.value) || null)

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
    const response = await fetch('/api/items')
    if (!response.ok) {
      throw new Error('Queue could not be loaded')
    }

    const payload = await response.json()
    items.value = payload.items
    currentReviewer.value = payload.current_reviewer
    activeCount.value = payload.active_count
    terminalCount.value = payload.terminal_count

    const preferredStillActive = items.value.some((item) => item.id === preferredId)
    selectedId.value = preferredStillActive ? preferredId : items.value[0]?.id || null
  } catch (loadError) {
    error.value = loadError.message
  } finally {
    loading.value = false
  }
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
        <h1>Active Queue</h1>
      </div>
      <dl class="metrics" aria-label="Queue summary">
        <div>
          <dt>Reviewer</dt>
          <dd>{{ currentReviewer }}</dd>
        </div>
        <div>
          <dt>Active</dt>
          <dd>{{ activeCount }}</dd>
        </div>
        <div>
          <dt>Closed</dt>
          <dd>{{ terminalCount }}</dd>
        </div>
      </dl>
    </header>

    <p v-if="feedback" class="feedback" role="status">{{ feedback }}</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <div v-if="loading" class="loading">Loading queue...</div>

    <section v-else class="layout" aria-label="Reviewer queue workspace">
      <aside class="queue" aria-label="Items needing review">
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

        <p v-if="items.length === 0" class="empty">No active items</p>
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
        <h2>Queue clear</h2>
      </article>
    </section>
  </main>
</template>
