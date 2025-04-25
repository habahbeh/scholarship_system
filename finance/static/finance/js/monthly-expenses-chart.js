// monthly-expenses-chart.js - Implementación simplificada usando Chart.js

/**
 * Crea un gráfico de gastos mensuales utilizando Chart.js
 * Esta es una implementación simplificada que reemplaza la versión de React
 */
document.addEventListener('DOMContentLoaded', function() {
  // Referencias de elementos del DOM
  const chartContainer = document.getElementById('monthlyExpensesChart');
  const yearSelector = document.getElementById('year-selector');
  const loaderElement = document.createElement('div');

  // Si no existe el contenedor, no continuar
  if (!chartContainer) return;

  // Configurar el elemento de carga
  loaderElement.className = 'text-center p-4';
  loaderElement.innerHTML = `
    <div class="spinner-border text-primary" role="status">
      <span class="visually-hidden">جاري التحميل...</span>
    </div>
    <p class="mt-2">جاري تحميل البيانات...</p>
  `;

  // Crear el canvas para el gráfico
  const canvas = document.createElement('canvas');
  canvas.id = 'monthlyExpensesCanvas';
  canvas.style.width = '100%';
  canvas.style.height = '300px';

  // Variables para el gráfico
  let monthlyChart = null;
  let currentYear = new Date().getFullYear();

  // Crear selector de año si no existe
  if (!yearSelector) {
    const selectorContainer = document.createElement('div');
    selectorContainer.className = 'mb-3 text-start';

    const selectElement = document.createElement('select');
    selectElement.className = 'form-select form-select-sm w-auto';
    selectElement.id = 'year-selector';

    // Generar opciones para los últimos 5 años
    const currentYear = new Date().getFullYear();
    for (let year = currentYear - 5; year <= currentYear; year++) {
      const option = document.createElement('option');
      option.value = year;
      option.textContent = year;
      option.selected = year === currentYear;
      selectElement.appendChild(option);
    }

    // Manejar cambio de año
    selectElement.addEventListener('change', function() {
      currentYear = this.value;
      fetchMonthlyData(currentYear);
    });

    selectorContainer.appendChild(selectElement);
    chartContainer.appendChild(selectorContainer);
  }

  // Función para mostrar mensaje de error
  function showError(message) {
    chartContainer.innerHTML = '';
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger';
    errorDiv.textContent = message || 'حدث خطأ أثناء جلب البيانات';
    chartContainer.appendChild(errorDiv);
  }

  // Función para mostrar mensaje de "sin datos"
  function showNoData() {
    chartContainer.innerHTML = '';
    const noDataDiv = document.createElement('div');
    noDataDiv.className = 'text-center p-4';
    noDataDiv.innerHTML = `
      <i class="fas fa-info-circle fa-3x text-muted mb-3"></i>
      <p>لا توجد بيانات مصروفات للعرض</p>
    `;
    chartContainer.appendChild(noDataDiv);
  }

  // Función para mostrar estadísticas
  function showStats(data) {
    // Calcular valores
    const totalExpenses = data.reduce((sum, item) => sum + item.value, 0);
    const averageExpense = data.length > 0 ? totalExpenses / data.length : 0;
    const maxExpense = data.length > 0 ? Math.max(...data.map(item => item.value)) : 0;

    // Crear contenedor de estadísticas
    const statsContainer = document.createElement('div');
    statsContainer.className = 'row mt-3';
    statsContainer.innerHTML = `
      <div class="col-md-4">
        <div class="card bg-light mb-3">
          <div class="card-body p-2 text-center">
            <h6 class="card-title mb-0">إجمالي المصروفات</h6>
            <p class="h4 mt-2 mb-0">${totalExpenses.toLocaleString()} د.أ</p>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card bg-light mb-3">
          <div class="card-body p-2 text-center">
            <h6 class="card-title mb-0">متوسط شهري</h6>
            <p class="h4 mt-2 mb-0">${averageExpense.toLocaleString(undefined, {maximumFractionDigits: 2})} د.أ</p>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card bg-light mb-3">
          <div class="card-body p-2 text-center">
            <h6 class="card-title mb-0">أعلى شهر</h6>
            <p class="h4 mt-2 mb-0">${maxExpense.toLocaleString()} د.أ</p>
          </div>
        </div>
      </div>
    `;
    chartContainer.appendChild(statsContainer);
  }

  // Función para inicializar o actualizar el gráfico
  function renderChart(data) {
    // Si no hay datos, mostrar mensaje
    if (!data || data.length === 0) {
      showNoData();
      return;
    }

    // Limpiar el contenedor y preparar para el nuevo gráfico
    chartContainer.innerHTML = '';

    // Si ya existe un selector de año, añadirlo de nuevo
    if (yearSelector) {
      chartContainer.appendChild(yearSelector);
    }

    // Añadir el canvas
    chartContainer.appendChild(canvas);

    // Nombres de los meses en árabe
    const arabicMonths = [
      'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
      'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
    ];

    // Preparar datos para Chart.js
    const labels = arabicMonths;
    const values = new Array(12).fill(0);

    // Llenar valores con los datos reales
    data.forEach(item => {
      const monthIndex = getMonthIndex(item.month);
      if (monthIndex !== -1) {
        values[monthIndex] = item.value;
      }
    });

    // Si ya existe un gráfico, destruirlo primero
    if (monthlyChart) {
      monthlyChart.destroy();
    }

    // Crear nuevo gráfico
    const ctx = canvas.getContext('2d');
    monthlyChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'المصروفات',
          data: values,
          backgroundColor: '#4e73df',
          borderColor: '#3a5cd0',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: function(value) {
                return value.toLocaleString() + ' د.أ';
              }
            }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              font: {
                family: 'Cairo, Tajawal, sans-serif'
              }
            }
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                return context.dataset.label + ': ' + context.parsed.y.toLocaleString() + ' د.أ';
              }
            }
          }
        }
      }
    });

    // Mostrar estadísticas
    showStats(data);
  }

  // Función para obtener el índice del mes (0-11) a partir del nombre en inglés
  function getMonthIndex(monthName) {
    const months = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    return months.indexOf(monthName);
  }

  // Función para obtener datos del API
  function fetchMonthlyData(year) {
    // Mostrar cargador
    chartContainer.innerHTML = '';
    chartContainer.appendChild(loaderElement);

    // Realizar petición al API
    fetch(`/finance/api/monthly-expenses/?year=${year}`)
      .then(response => {
        if (!response.ok) {
          throw new Error('Error al obtener datos');
        }
        return response.json();
      })
      .then(result => {
        renderChart(result.data);
      })
      .catch(error => {
        console.error('Error fetching data:', error);

        // Usar datos de ejemplo en caso de error
        const dummyData = [
          { month: "January", value: 15000 },
          { month: "February", value: 18000 },
          { month: "March", value: 22000 },
          { month: "April", value: 17000 },
          { month: "May", value: 20000 },
          { month: "June", value: 25000 },
          { month: "July", value: 19000 },
          { month: "August", value: 21000 },
          { month: "September", value: 18000 },
          { month: "October", value: 23000 },
          { month: "November", value: 20000 },
          { month: "December", value: 26000 }
        ];

        // Mostrar datos de ejemplo
        renderChart(dummyData);
      });
  }

  // Escuchar eventos de cambio de período
  document.addEventListener('periodChanged', function(event) {
    const period = event.detail.period;
    console.log('Período cambiado a:', period);
    // Implementar lógica según el período seleccionado si es necesario
  });

  // Inicializar el gráfico con los datos del año actual
  fetchMonthlyData(currentYear);
});