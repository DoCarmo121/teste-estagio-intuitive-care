<script setup>
import { ref, onMounted, watch } from 'vue'
import axios from 'axios'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const API_URL = 'http://localhost:8000/api'

// --- ESTADOS ---
const operadoras = ref([])
const totalItems = ref(0)
const page = ref(1)
const search = ref('')
const loading = ref(false)
const stats = ref(null)
const chartData = ref({ labels: [], datasets: [] })
const selectedOp = ref(null)
const history = ref([])
const showModal = ref(false)

// --- AÇÕES ---
const fetchOperadoras = async () => {
  loading.value = true
  try {
    const res = await axios.get(`${API_URL}/operadoras`, {
      params: { page: page.value, limit: 10, search: search.value }
    })
    operadoras.value = res.data.data
    totalItems.value = res.data.total
  } catch (error) {
    console.error("Erro API:", error)
  } finally {
    loading.value = false
  }
}

const fetchStats = async () => {
  try {
    const res = await axios.get(`${API_URL}/estatisticas`)
    stats.value = res.data

    // REQUISITO 4.3: Gráfico com distribuição por UF
    const labels = res.data.top_estados.map(item => item.nome)
    const values = res.data.top_estados.map(item => item.total)

    chartData.value = {
      labels: labels,
      datasets: [{ label: 'Despesas por Estado (R$)', data: values, backgroundColor: '#42b883' }]
    }
  } catch (error) {
    console.error("Erro stats:", error)
  }
}

const openDetails = async (op) => {
  selectedOp.value = op
  showModal.value = true
  history.value = []
  if (!op.cnpj) return
  try {
    const cnpjSafe = op.cnpj.replace(/[^0-9]/g, '')
    const res = await axios.get(`${API_URL}/operadoras/${cnpjSafe}/despesas`)
    history.value = res.data
  } catch (error) { console.error(error) }
}

watch(page, fetchOperadoras)
watch(search, () => { page.value = 1; fetchOperadoras() })

onMounted(() => { fetchOperadoras(); fetchStats() })
</script>

<template>
  <div class="container">
    <header><h1>🏥 Intuitive Care - Dashboard</h1></header>

    <section class="stats-panel" v-if="stats">
      <div class="kpi-group">
        <div class="card kpi">
          <h3>Total Despesas</h3>
          <p class="big-number">R$ {{ stats.total_despesas.toLocaleString('pt-BR', { notation: 'compact', style: 'currency', currency: 'BRL' }) }}</p>
        </div>
        <div class="card kpi">
          <h3>Média / Operadora</h3>
          <p class="big-number">R$ {{ stats.media_por_operadora.toLocaleString('pt-BR', { notation: 'compact', style: 'currency', currency: 'BRL' }) }}</p>
        </div>
      </div>

      <div class="card chart-container">
        <h3>Despesas por Estado (Top 10)</h3>
        <Bar v-if="chartData.labels.length" :data="chartData" :options="{ responsive: true, maintainAspectRatio: false }" />
      </div>
    </section>

    <div class="controls-top">
      <input v-model.lazy="search" placeholder="🔍 Buscar por Razão Social ou CNPJ..." class="search-input" />
      <span class="total-badge" v-if="totalItems">Encontrados: {{ totalItems }}</span>
    </div>

    <div class="table-wrapper">
      <div v-if="loading" class="loading">Carregando...</div>
      <table v-else>
        <thead><tr><th>Reg. ANS</th><th>CNPJ</th><th>Razão Social</th><th>UF</th><th>Ações</th></tr></thead>
        <tbody>
          <tr v-for="op in operadoras" :key="op.registro_ans">
            <td>{{ op.registro_ans }}</td><td>{{ op.cnpj }}</td><td>{{ op.razao_social }}</td><td>{{ op.uf }}</td>
            <td><button class="btn-detail" @click="openDetails(op)">Detalhes</button></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pagination-footer">
      <button @click="page--" :disabled="page <= 1">◀ Anterior</button>
      <span class="page-info">Página <strong>{{ page }}</strong></span>
      <button @click="page++" :disabled="operadoras.length < 10">Próximo ▶</button>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <h2>{{ selectedOp.razao_social }}</h2>
        <p>CNPJ: {{ selectedOp.cnpj }} | UF: {{ selectedOp.uf }}</p>
        <h3>Histórico Financeiro</h3>
        <div class="history-list">
          <div v-for="h in history" :key="h.data_referencia" class="history-item">
            <span>{{ h.trimestre }}º Tri / {{ h.ano }}</span><span class="value">R$ {{ h.valor_despesa.toLocaleString('pt-BR') }}</span>
          </div>
          <div v-if="history.length === 0">Sem registros.</div>
        </div>
        <button @click="showModal = false" class="close-btn">Fechar</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.container { max-width: 1100px; margin: 0 auto; font-family: 'Segoe UI', sans-serif; padding: 20px; color: #2c3e50; }
.stats-panel { display: grid; grid-template-columns: 1fr 2fr; gap: 20px; margin-bottom: 30px; }
.kpi-group { display: flex; flex-direction: column; gap: 20px; }
.card { background: #fff; padding: 20px; border-radius: 12px; border: 1px solid #eee; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
.kpi { text-align: center; display: flex; flex-direction: column; justify-content: center; height: 100%; }
.big-number { font-size: 1.8em; font-weight: bold; color: #42b883; margin-top: 5px; }
.chart-container { height: 300px; }

/* Controles Topo */
.controls-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
.search-input { padding: 12px; width: 100%; max-width: 400px; border: 1px solid #ccc; border-radius: 6px; font-size: 1rem; }
.total-badge { background: #eee; padding: 5px 10px; border-radius: 15px; font-size: 0.9em; color: #666; }

/* Tabela */
.table-wrapper { min-height: 300px; }
table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
th { background-color: #2c3e50; color: white; padding: 12px; text-align: left; }
td { padding: 12px; border-bottom: 1px solid #eee; }
.btn-detail { background: #3498db; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }

/* Paginação Rodapé */
.pagination-footer { display: flex; justify-content: center; align-items: center; gap: 20px; margin-top: 20px; padding: 20px 0; border-top: 1px solid #eee; }
.pagination-footer button { padding: 10px 20px; background: #2c3e50; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; transition: background 0.2s; }
.pagination-footer button:hover:not(:disabled) { background: #34495e; }
.pagination-footer button:disabled { background: #95a5a6; cursor: not-allowed; opacity: 0.7; }
.page-info { font-size: 1.1em; color: #555; }

/* Modal */
.modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); display: flex; justify-content: center; align-items: center; z-index: 1000; }
.modal { background: white; padding: 30px; border-radius: 12px; width: 500px; max-height: 85vh; overflow-y: auto; }
.history-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }
.close-btn { margin-top: 20px; background: #e74c3c; color: white; border: none; padding: 10px; width: 100%; border-radius: 6px; cursor: pointer; }
</style>