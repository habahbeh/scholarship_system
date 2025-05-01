// قم بوضع هذا الملف في مجلد finance/static/finance/js/dashboard.js

document.addEventListener('DOMContentLoaded', function() {
  // Initialize all React chart components
  initializeCharts();

  // Handle period selector events
  setupEventListeners();

  // Setup any other dashboard functionality
  setupDashboardActions();
});

/**
 * تهيئة جميع المخططات في لوحة المعلومات
 */
function initializeCharts() {
  const monthlyExpensesContainer = document.getElementById('monthlyExpensesChart');
  const categoryExpensesContainer = document.getElementById('categoryExpensesChart');
  const budgetStatusContainer = document.getElementById('budgetStatusChart');

  // Check if React and ReactDOM are loaded
  if (typeof React === 'undefined' || typeof ReactDOM === 'undefined') {
    console.error('React or ReactDOM is not loaded. Charts will not be displayed.');

    // Show error message in containers
    const errorMessage = `
      <div class="alert alert-danger" role="alert">
        <i class="fas fa-exclamation-triangle me-2"></i>
        خطأ في تحميل مكتبات الرسوم البيانية. يرجى تحديث الصفحة أو الاتصال بالدعم الفني.
      </div>
    `;

    if (monthlyExpensesContainer) monthlyExpensesContainer.innerHTML = errorMessage;
    if (categoryExpensesContainer) categoryExpensesContainer.innerHTML = errorMessage;
    if (budgetStatusContainer) budgetStatusContainer.innerHTML = errorMessage;

    return;
  }

  // Initialize monthly expenses chart
  if (monthlyExpensesContainer && typeof MonthlyExpensesChart !== 'undefined') {
    try {
      ReactDOM.render(React.createElement(MonthlyExpensesChart), monthlyExpensesContainer);
      console.log('Monthly expenses chart initialized');
    } catch (error) {
      console.error('Error initializing monthly expenses chart:', error);
      monthlyExpensesContainer.innerHTML = `
        <div class="alert alert-danger" role="alert">
          <i class="fas fa-exclamation-triangle me-2"></i>
          خطأ في تهيئة مخطط المصروفات الشهرية
        </div>
      `;
    }
  } else {
    console.warn('Monthly expenses chart container or component not found');
  }

  // Initialize category expenses chart
  if (categoryExpensesContainer && typeof CategoryExpensesChart !== 'undefined') {
    try {
      ReactDOM.render(React.createElement(CategoryExpensesChart), categoryExpensesContainer);
      console.log('Category expenses chart initialized');
    } catch (error) {
      console.error('Error initializing category expenses chart:', error);
      categoryExpensesContainer.innerHTML = `
        <div class="alert alert-danger" role="alert">
          <i class="fas fa-exclamation-triangle me-2"></i>
          خطأ في تهيئة مخطط المصروفات حسب الفئة
        </div>
      `;
    }
  } else {
    console.warn('Category expenses chart container or component not found');
  }

  // Initialize budget status chart
  if (budgetStatusContainer && typeof BudgetStatusChart !== 'undefined') {
    try {
      ReactDOM.render(React.createElement(BudgetStatusChart), budgetStatusContainer);
      console.log('Budget status chart initialized');
    } catch (error) {
      console.error('Error initializing budget status chart:', error);
      budgetStatusContainer.innerHTML = `
        <div class="alert alert-danger" role="alert">
          <i class="fas fa-exclamation-triangle me-2"></i>
          خطأ في تهيئة مخطط حالة الميزانية
        </div>
      `;
    }
  } else {
    console.warn('Budget status chart container or component not found');
  }
}

/**
 * تهيئة أحداث المستمع لعناصر لوحة المعلومات
 */
function setupEventListeners() {
  // Handle period selector changes
  const periodSelector = document.getElementById('period-selector');
  if (periodSelector) {
    periodSelector.addEventListener('change', function(e) {
      const period = e.target.value;
      console.log('Period changed to:', period);

      // Dispatch custom event for chart components to listen for
      const event = new CustomEvent('periodChanged', { detail: { period } });
      document.dispatchEvent(event);
    });
  }

  // Handle export report button
  const exportReportBtn = document.querySelector('.btn-outline-secondary');
  if (exportReportBtn) {
    exportReportBtn.addEventListener('click', function() {
      alert('سيتم تصدير التقرير قريباً');
      // Implementation for report export would go here
    });
  }

  // Handle chart filter buttons
  const filterButtons = document.querySelectorAll('.btn-group .btn-outline-secondary');
  if (filterButtons.length > 0) {
    filterButtons.forEach(button => {
      button.addEventListener('click', function() {
        // Remove active class from all buttons
        filterButtons.forEach(btn => btn.classList.remove('active'));

        // Add active class to clicked button
        this.classList.add('active');

        // Get category filter
        const category = this.textContent.trim();
        console.log('Filter by category:', category);

        // Implement filtering logic here
        // For now we'll just log the selected category
      });
    });
  }
}

/**
 * تهيئة أي وظائف إضافية للوحة المعلومات
 */
function setupDashboardActions() {
  // Add any additional dashboard functionality here
  console.log('Dashboard initialized successfully');

  // Example: Auto-refresh data every 5 minutes
  // setInterval(refreshDashboardData, 5 * 60 * 1000);
}

/**
 * تحديث بيانات لوحة المعلومات (مثال لوظيفة تحديث)
 */
function refreshDashboardData() {
  console.log('Refreshing dashboard data...');
  // Implementation for refreshing data would go here
  // This could involve reinitializing charts or making API calls
}