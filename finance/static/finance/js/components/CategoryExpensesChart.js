import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

const CategoryExpensesChart = () => {
  // State to store category data
  const [categoryData, setCategoryData] = useState([]);
  // State to track loading status
  const [loading, setLoading] = useState(true);
  // State to track any errors
  const [error, setError] = useState(null);

  // Colors for different categories
  const COLORS = ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#5a5c69', '#858796', '#3a3b45'];

  // Fetch category expenses data
  useEffect(() => {
    const fetchCategoryData = async () => {
      setLoading(true);
      try {
        // Use the API endpoint from your Django views
        const response = await fetch('/finance/api/expense-categories/');

        if (!response.ok) {
          throw new Error('Failed to fetch data');
        }

        const result = await response.json();
        setCategoryData(result.data);
        setError(null);
      } catch (err) {
        console.error('Error fetching category expense data:', err);
        setError('حدث خطأ أثناء جلب البيانات. يرجى المحاولة مرة أخرى لاحقاً.');

        // Set dummy data for demonstration if API fails
        setCategoryData([
          { name: "الرسوم الدراسية", value: 45000 },
          { name: "السكن", value: 30000 },
          { name: "المواصلات", value: 10000 },
          { name: "الكتب والمراجع", value: 8000 },
          { name: "المعيشة", value: 25000 },
          { name: "أخرى", value: 12000 }
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchCategoryData();
  }, []);

  // Calculate total expenses
  const totalExpenses = categoryData.reduce((sum, item) => sum + item.value, 0);

  // Custom tooltip for the chart
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const percentage = ((data.value / totalExpenses) * 100).toFixed(1);

      return (
        <div className="bg-white p-2 border shadow-sm">
          <p className="mb-1 fw-bold">{data.name}</p>
          <p className="mb-0">{data.value.toLocaleString()} د.أ ({percentage}%)</p>
        </div>
      );
    }
    return null;
  };

  // Custom legend to show percentages
  const renderCustomizedLegend = (props) => {
    const { payload } = props;

    return (
      <ul className="ps-0 mt-2" style={{ listStyle: 'none' }}>
        {payload.map((entry, index) => {
          const percentage = ((entry.payload.value / totalExpenses) * 100).toFixed(1);
          return (
            <li key={`item-${index}`} className="mb-1 d-flex align-items-center">
              <div
                style={{
                  backgroundColor: entry.color,
                  width: '12px',
                  height: '12px',
                  marginRight: '8px'
                }}
              />
              <span className="small text-muted">{entry.value} ({percentage}%)</span>
            </li>
          );
        })}
      </ul>
    );
  };

  return (
    <div className="chart-wrapper">
      {loading ? (
        <div className="text-center p-4">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">جاري التحميل...</span>
          </div>
          <p className="mt-2">جاري تحميل البيانات...</p>
        </div>
      ) : error ? (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      ) : categoryData.length === 0 ? (
        <div className="text-center p-4">
          <i className="fas fa-info-circle fa-3x text-muted mb-3"></i>
          <p>لا توجد بيانات مصروفات للعرض</p>
        </div>
      ) : (
        <>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={categoryData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                fill="#8884d8"
                paddingAngle={3}
                dataKey="value"
                label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {categoryData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend
                content={renderCustomizedLegend}
                layout="vertical"
                align="right"
                verticalAlign="middle"
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="text-center mt-3">
            <p className="mb-1">إجمالي المصروفات</p>
            <h5>{totalExpenses.toLocaleString()} د.أ</h5>
          </div>
        </>
      )}
    </div>
  );
};

export default CategoryExpensesChart;