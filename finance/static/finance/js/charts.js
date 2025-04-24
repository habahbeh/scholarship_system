// وظائف الرسوم البيانية للنظام المالي

// إنشاء مخطط دائري لملخص الميزانية
function createBudgetPieChart(data) {
    var ctx = document.getElementById('budgetPieChart');
    if (!ctx) return;

    var chart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.pie_data.map(item => item.name),
            datasets: [{
                data: data.pie_data.map(item => item.value),
                backgroundColor: [
                    '#4bc0c0',
                    '#ff6384',
                    '#36a2eb',
                    '#ffcd56',
                    '#9966ff',
                    '#c9cbcf'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            var label = context.label || '';
                            var value = context.raw;
                            var total = context.dataset.data.reduce((a, b) => a + b, 0);
                            var percentage = Math.round((value / total) * 100);
                            return label + ': ' + value.toLocaleString() + ' ريال (' + percentage + '%)';
                        }
                    }
                }
            }
        }
    });
}

// إنشاء مخطط دائري للمصروفات حسب الفئة
function createCategoryExpensesChart(data) {
    var ctx = document.getElementById('categoryExpensesChart');
    if (!ctx) return;

    var chart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.data.map(item => item.name),
            datasets: [{
                data: data.data.map(item => item.value),
                backgroundColor: [
                    '#ff6384',
                    '#36a2eb',
                    '#ffcd56',
                    '#4bc0c0',
                    '#9966ff',
                    '#ff9f40',
                    '#c9cbcf',
                    '#4d5360'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            var label = context.label || '';
                            var value = context.raw;
                            var total = context.dataset.data.reduce((a, b) => a + b, 0);
                            var percentage = Math.round((value / total) * 100);
                            return label + ': ' + value.toLocaleString() + ' ريال (' + percentage + '%)';
                        }
                    }
                }
            }
        }
    });
}

// إنشاء مخطط شريطي للمصروفات الشهرية
function createMonthlyExpensesChart(data) {
    var ctx = document.getElementById('monthlyExpensesChart');
    if (!ctx) return;

    var chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.data.map(item => item.month),
            datasets: [{
                label: 'المصروفات الشهرية',
                data: data.data.map(item => item.value),
                backgroundColor: 'rgba(54, 162, 235, 0.5)',
                borderColor: 'rgba(54, 162, 235, 1)',
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
                        callback: function(value, index, values) {
                            return value.toLocaleString() + ' ريال';
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.raw.toLocaleString() + ' ريال';
                        }
                    }
                }
            }
        }
    });
}

// إنشاء مخطط دونات لحالة الميزانيات
function createBudgetStatusChart(data) {
    var ctx = document.getElementById('budgetStatusChart');
    if (!ctx) return;

    var chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.data.map(item => item.name),
            datasets: [{
                data: data.data.map(item => item.value),
                backgroundColor: [
                    '#28a745',  // نشطة
                    '#ffc107',  // معلقة
                    '#6c757d'   // مغلقة
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}