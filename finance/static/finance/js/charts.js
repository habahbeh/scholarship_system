// وظائف الرسوم البيانية للنظام المالي - نسخة محسنة

// الألوان الموحدة للمخططات
const chartColors = {
    primary: '#2196F3',
    secondary: '#78909C',
    success: '#4CAF50',
    danger: '#F44336',
    warning: '#FFC107',
    info: '#03A9F4',
    // مجموعة ألوان متناسقة للمخططات الدائرية
    pieColors: [
        '#2196F3', // أزرق
        '#4CAF50', // أخضر
        '#FFC107', // أصفر
        '#F44336', // أحمر
        '#9C27B0', // أرجواني
        '#3F51B5', // نيلي
        '#FF9800', // برتقالي
        '#00BCD4', // فيروزي
        '#009688', // أخضر فاتح
        '#E91E63'  // وردي
    ]
};

// خيارات موحدة للمخططات
const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
        duration: 1000,
        easing: 'easeOutQuart'
    },
    plugins: {
        legend: {
            labels: {
                font: {
                    family: 'Cairo, Tajawal, sans-serif',
                    size: 13
                },
                color: '#546e7a',
                usePointStyle: true,
                padding: 20
            }
        },
        tooltip: {
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            titleColor: '#37474f',
            bodyColor: '#546e7a',
            borderColor: '#e9ecef',
            borderWidth: 1,
            cornerRadius: 8,
            boxPadding: 6,
            usePointStyle: true,
            titleFont: {
                family: 'Cairo, Tajawal, sans-serif',
                size: 14,
                weight: 'bold'
            },
            bodyFont: {
                family: 'Cairo, Tajawal, sans-serif',
                size: 13
            },
            padding: 12,
            caretSize: 6
        }
    }
};

// إنشاء مخطط دائري لملخص