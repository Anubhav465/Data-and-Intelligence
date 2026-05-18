import { Bar, Pie, Line, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  LineElement,
  PointElement,
  Filler,
} from 'chart.js';
import { motion } from 'framer-motion';
import './ChartRenderer.css';

ChartJS.register(
  CategoryScale, LinearScale, BarElement,
  Title, Tooltip, Legend, ArcElement,
  LineElement, PointElement, Filler
);

// Futuristic neon palette
const PALETTE = [
  '#22d3ee', '#a855f7', '#34d399', '#f59e0b',
  '#ec4899', '#6366f1', '#10b981', '#f97316',
  '#06b6d4', '#8b5cf6', '#14b8a6', '#ef4444',
];

const buildDatasets = (datasets, type) =>
  datasets.map((ds, idx) => {
    const color = PALETTE[idx % PALETTE.length];
    const isArea = type === 'line';
    return {
      ...ds,
      backgroundColor: ['pie', 'doughnut'].includes(type)
        ? PALETTE.slice(0, (ds.data?.length || PALETTE.length))
        : isArea
        ? `${color}22`
        : `${color}cc`,
      borderColor: color,
      borderWidth: 2,
      pointBackgroundColor: color,
      pointBorderColor: '#020617',
      pointBorderWidth: 2,
      pointRadius: type === 'line' ? 4 : 0,
      pointHoverRadius: 6,
      hoverBackgroundColor: color,
      fill: isArea,
      tension: 0.4,
    };
  });

const getOptions = (type) => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 800, easing: 'easeInOutQuart' },
  plugins: {
    legend: {
      position: 'top',
      labels: {
        color: '#94a3b8',
        font: { size: 11, family: 'Inter, system-ui, sans-serif' },
        boxWidth: 10,
        padding: 16,
        usePointStyle: true,
      },
    },
    tooltip: {
      backgroundColor: 'rgba(10, 20, 45, 0.96)',
      titleColor: '#22d3ee',
      bodyColor: '#e2e8f0',
      borderColor: 'rgba(34,211,238,0.25)',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 10,
      displayColors: true,
      titleFont: { family: 'Inter, system-ui, sans-serif', weight: '600' },
      bodyFont: { family: 'Inter, system-ui, sans-serif' },
      callbacks: {
        label: (ctx) => {
          const val = ctx.parsed?.y ?? ctx.parsed;
          const num = typeof val === 'number' ? val.toLocaleString() : val;
          return ` ${ctx.dataset.label || ''}: ${num}`;
        },
      },
    },
  },
  scales: ['bar', 'line'].includes(type)
    ? {
        x: {
          grid: { color: 'rgba(34,211,238,0.06)', drawBorder: false },
          ticks: {
            color: '#64748b',
            font: { size: 10, family: 'Inter, system-ui, sans-serif' },
            maxRotation: 35,
          },
          border: { color: 'rgba(34,211,238,0.1)' },
        },
        y: {
          grid: { color: 'rgba(34,211,238,0.06)', drawBorder: false },
          ticks: {
            color: '#64748b',
            font: { size: 10, family: 'Inter, system-ui, sans-serif' },
            callback: (v) =>
              Math.abs(v) >= 1_000_000
                ? `${(v / 1_000_000).toFixed(1)}M`
                : Math.abs(v) >= 1_000
                ? `${(v / 1_000).toFixed(1)}k`
                : v,
          },
          border: { color: 'rgba(34,211,238,0.1)' },
        },
      }
    : {},
});

const ChartRenderer = ({ chartSpec }) => {
  if (!chartSpec?.data?.labels) return null;

  const type = chartSpec.type || 'bar';
  const data = {
    labels: chartSpec.data.labels,
    datasets: buildDatasets(chartSpec.data.datasets || [], type),
  };
  const options = getOptions(type);
  const props = { data, options };

  const ChartMap = { bar: Bar, pie: Pie, line: Line, doughnut: Doughnut };
  const ChartComponent = ChartMap[type];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="chart-container"
    >
      <div className="chart-canvas" style={{ height: ['pie', 'doughnut'].includes(type) ? 320 : 300 }}>
        {ChartComponent ? (
          <ChartComponent {...props} />
        ) : (
          <p className="chart-unsupported">Unsupported chart type: {type}</p>
        )}
      </div>
    </motion.div>
  );
};

export default ChartRenderer;
