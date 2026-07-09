'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import type { ApexOptions } from 'apexcharts';

// ✅ Dynamically import ApexCharts only on the client
const ReactApexChart = dynamic(() => import('react-apexcharts'), { ssr: false });

interface DonutChartState {
  series: number[];
  options: ApexOptions;
}

const ApexDonutChart: React.FC = () => {
  const [state] = React.useState<DonutChartState>({
    series: [54, 35, 13, 27],
    options: {
      chart: {
        type: 'donut',
        width: 320,
      },
      labels: ['Success', 'Processing', 'Failed', 'Pending'],
      dataLabels: { enabled: false },
      responsive: [
        {
          breakpoint: 480,
          options: {
            chart: { width: 200 },
            legend: { show: false },
          },
        },
      ],
      legend: {
        position: 'right',
        offsetY: 0,
        height: 230,
        labels: { colors: ['#000'] },
      },
      colors: [
        'var(--color-primary-500)',
        'rgb(0, 227, 150)',
        'rgb(255, 69, 96)',
        'rgb(254, 176, 25)',
      ],
    },
  });

  return (
    <div className="flex flex-col items-center gap-4 p-4 bg-white rounded-lg">
      <ReactApexChart
        options={state.options}
        series={state.series}
        type="donut"
        width={350}
      />
    </div>
  );
};

export default ApexDonutChart;
