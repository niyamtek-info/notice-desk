'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import type { ApexOptions } from 'apexcharts';

// Dynamically import ReactApexChart to avoid SSR issues
const ReactApexChart = dynamic(() => import('react-apexcharts'), { ssr: false });

const ApexChart: React.FC = () => {
  const categories = ['Sep', 'Oct', 'Nov', 'Dec', 'Jan'];
  const data = [0.3, 0.5, 0.7, 0.6, 0.9];

  const series = [
    {
      name: 'Inflation',
      data: data,
    },
  ];

  const options: ApexOptions = {
    chart: {
      height: 350,
      type: 'bar',
      toolbar: { show: false },
    },
    plotOptions: {
      bar: {
        borderRadius: 5,
        columnWidth: '50%',
        dataLabels: { position: 'top' },
      },
    },
    colors: ['var(--color-primary-500)'],
    dataLabels: {
      enabled: true,
      formatter: (val: number) => `${val}%`,
      offsetY: -20,
      style: { fontSize: '12px', colors: ['#304758'] },
    },
    xaxis: {
      categories,
      position: 'top',
      axisBorder: { show: false },
      axisTicks: { show: false },
      tooltip: { enabled: true },
    },
    yaxis: {
      axisBorder: { show: false },
      axisTicks: { show: false },
      labels: { show: false, formatter: (val: number) => `${val}%` },
    },
  };

  return <ReactApexChart options={options} series={series} type="bar" height={280}  />;
};

export default ApexChart;
