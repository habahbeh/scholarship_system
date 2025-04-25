// يجب وضع هذا الملف في مجلد finance/static/finance/js/components/BudgetStatusChart.js

(function(window) {
  const { useState, useEffect } = React;
  const { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } = Recharts;

  const BudgetStatusChart = () => {
    // State to store budget status data
    const [budgetData, setBudgetData] = useState([]);
    // State to track loading status
    const [loading, setLoading] = useState(true);
    // State to track any errors
    const [error, setError] = useState(null);

    // Status colors
    const STATUS_COLORS = {
      'نشطة': '#1cc88a',    // Active - green
      'معلقة': '#f6c23e',    // Pending - yellow
      'مغلقة': '#858796'     // Closed - gray
    };

    // Fetch budget status data
    useEffect(() => {
      const fetchBudgetData = async () => {
        setLoading(true);
        try {
          // Use the API endpoint from your Django views
          const response = await fetch('/finance/api/budget-status/');

          if (!response.ok) {
            throw new Error('Failed to fetch data');
          }

          const result = await response.json();
          setBudgetData(result.data);
          setError(null);
        } catch (err) {
          console.error('Error fetching budget status data:', err);
          setError('حدث خطأ أثناء جلب البيانات');

          // Set dummy data for demonstration if API fails
          setBudgetData([
            { name: "نشطة", value: 18 },
            { name: "معلقة", value: 7 },
            { name: "مغلقة", value: 5 }
          ]);
        } finally {
          setLoading(false);
        }
      };

      fetchBudgetData();
    }, []);

    // Custom tooltip for the chart
    const CustomTooltip = ({ active, payload }) => {
      if (active && payload && payload.length) {
        const data = payload[0].payload;
        const totalBudgets = budgetData.reduce((sum, item) => sum + item.value, 0);
        const percentage = ((data.value / totalBudgets) * 100).toFixed(1);

        return (
          <div className="bg-white p-2 border shadow-sm">
            <p className="mb-1 fw-bold">{data.name}</p>
            <p className="mb-0">{data.value} ميزانية ({percentage}%)</p>
          </div>
        );
      }
      return null;
    };

    return (
      <div className="chart-wrapper">
        {loading ? (
          <div className="text-center py-3">
            <div className="spinner-border spinner-border-sm text-primary" role="status">
              <span className="visually-hidden">جاري التحميل...</span>
            </div>
          </div>
        ) : error ? (
          <div className="alert alert-danger py-2" role="alert">
            {error}
          </div>
        ) : budgetData.length === 0 ? (
          <div className="text-center py-3">
            <p className="text-muted mb-0">لا توجد بيانات للعرض</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={150}>
            <PieChart>
              <Pie
                data={budgetData}
                cx="50%"
                cy="50%"
                outerRadius={60}
                fill="#8884d8"
                dataKey="value"
                label={({ name, value }) => `${name}: ${value}`}
                labelLine={false}
              >
                {budgetData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={STATUS_COLORS[entry.name] || '#' + ((1 << 24) * Math.random() | 0).toString(16)}
                  />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
    );
  };

  // إضافة المكون إلى النافذة ليكون متاحًا للاستخدام من خلال ملف داشبورد
  window.BudgetStatusChart = BudgetStatusChart;
})(window);