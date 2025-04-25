import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const MonthlyExpensesChart = () => {
  // State to store the monthly expense data
  const [monthlyData, setMonthlyData] = useState([]);
  // State to track loading status
  const [loading, setLoading] = useState(true);
  // State to track any errors
  const [error, setError] = useState(null);
  // State for selected year (default to current year)
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

  // Arabic month names
  const arabicMonths = {
    'January': 'يناير',
    'February': 'فبراير',
    'March': 'مارس',
    'April': 'أبريل',
    'May': 'مايو',
    'June': 'يونيو',
    'July': 'يوليو',
    'August': 'أغسطس',
    'September': 'سبتمبر',
    'October': 'أكتوبر',
    'November': 'نوفمبر',
    'December': 'ديسمبر'
  };

  // Get list of available years (5 years back from current)
  const availableYears = Array.from(
    { length: 6 },
    (_, i) => new Date().getFullYear() - 5 + i
  );

  // Fetch monthly expenses data
  useEffect(() => {
    const fetchMonthlyData = async () => {
      setLoading(true);
      try {
        // Use the API endpoint from your Django views
        const response = await fetch(`/finance/api/monthly-expenses/?year=${selectedYear}`);

        if (!response.ok) {
          throw new Error('Failed to fetch data');
        }

        const result = await response.json();

        // Transform month names to Arabic
        const transformedData = result.data.map(item => ({
          ...item,
          month: arabicMonths[item.month] || item.month
        }));

        setMonthlyData(transformedData);
        setError(null);
      } catch (err) {
        console.error('Error fetching monthly expense data:', err);
        setError('حدث خطأ أثناء جلب البيانات. يرجى المحاولة مرة أخرى لاحقاً.');

        // Set dummy data for demonstration if API fails
        setMonthlyData([
          { month: "يناير", value: 15000 },
          { month: "فبراير", value: 18000 },
          { month: "مارس", value: 22000 },
          { month: "أبريل", value: 17000 },
          { month: "مايو", value: 20000 },
          { month: "يونيو", value: 25000 },
          { month: "يوليو", value: 19000 },
          { month: "أغسطس", value: 21000 },
          { month: "سبتمبر", value: 18000 },
          { month: "أكتوبر", value: 23000 },
          { month: "نوفمبر", value: 20000 },
          { month: "ديسمبر", value: 26000 }
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchMonthlyData();
  }, [selectedYear]);

  // Handle year selection change
  const handleYearChange = (e) => {
    setSelectedYear(parseInt(e.target.value));
  };

  return (
    <div className="chart-wrapper">
      {/* Year selector */}
      <div className="mb-3 text-start">
        <select
          className="form-select form-select-sm w-auto"
          value={selectedYear}
          onChange={handleYearChange}
        >
          {availableYears.map(year => (
            <option key={year} value={year}>{year}</option>
          ))}
        </select>
      </div>

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
      ) : monthlyData.length === 0 ? (
        <div className="text-center p-4">
          <i className="fas fa-info-circle fa-3x text-muted mb-3"></i>
          <p>لا توجد بيانات مصروفات للعرض</p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={monthlyData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 12 }}
            />
            <YAxis />
            <Tooltip
              formatter={(value) => [`${value.toLocaleString()} د.أ`, 'المصروفات']}
              labelFormatter={(label) => `شهر: ${label}`}
            />
            <Legend />
            <Bar
              dataKey="value"
              name="المصروفات"
              fill="#4e73df"
              barSize={40}
            />
          </BarChart>
        </ResponsiveContainer>
      )}

      {/* Summary statistics if data exists */}
      {!loading && !error && monthlyData.length > 0 && (
        <div className="row mt-3">
          <div className="col-md-4">
            <div className="card bg-light mb-3">
              <div className="card-body p-2 text-center">
                <h6 className="card-title mb-0">إجمالي المصروفات</h6>
                <p className="h4 mt-2 mb-0">
                  {monthlyData.reduce((sum, item) => sum + item.value, 0).toLocaleString()} د.أ
                </p>
              </div>
            </div>
          </div>

          <div className="col-md-4">
            <div className="card bg-light mb-3">
              <div className="card-body p-2 text-center">
                <h6 className="card-title mb-0">متوسط شهري</h6>
                <p className="h4 mt-2 mb-0">
                  {(monthlyData.reduce((sum, item) => sum + item.value, 0) / 12).toLocaleString(undefined, {maximumFractionDigits: 2})} د.أ
                </p>
              </div>
            </div>
          </div>

          <div className="col-md-4">
            <div className="card bg-light mb-3">
              <div className="card-body p-2 text-center">
                <h6 className="card-title mb-0">أعلى شهر</h6>
                <p className="h4 mt-2 mb-0">
                  {Math.max(...monthlyData.map(item => item.value)).toLocaleString()} د.أ
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MonthlyExpensesChart;