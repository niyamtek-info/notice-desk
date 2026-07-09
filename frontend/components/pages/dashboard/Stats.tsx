'use client';

import React from 'react';
import { FaChartLine, FaRegCheckCircle } from 'react-icons/fa';
import { PiTimerBold } from "react-icons/pi";
import { IoDocumentOutline } from 'react-icons/io5';

type Metric = {
  total: number;
  active: number;
  progress: number;
  success_rate: number;
};

type Job = {
  id: number;
  title: string;
  status: string;
};

const staticMetrics: Metric[] = [
  {
    total: 453,
    active: 132,
    progress: 78,
    success_rate: 95,
  },
];

const staticJobs: Job[] = [
  { id: 1, title: 'Job One', status: 'active' },
  { id: 2, title: 'Job Two', status: 'completed' },
];

const Stats: React.FC = () => {
  const metrics = staticMetrics;

  if (!metrics || metrics.length === 0) {
    return <div className="text-center py-10">Loading dashboard metrics...</div>;
  }

  const data = [
    {
      count: metrics[0].total,
      percentage: '',
      title: 'Total Loan Application',
      css: 'bg-blue-100 text-blue-800',
      border: 'border-primary-500',
      icon: <IoDocumentOutline className='text-[20px] text-primary-500' />,
    },
    {
      count: metrics[0].active,
      percentage: '',
      title: 'Loan Application Approved',
      css: 'bg-green-100 text-green-800',
      border: 'border-green-500',
      icon: <FaRegCheckCircle className='text-[19px] text-green-800' />,
    },
    {
      count: metrics[0].progress,
      percentage: '',
      title: 'Loan Application In Progress',
      css: 'bg-red-100 ',
      border: 'border-red-500',
      icon: <PiTimerBold className='text-[20px] text-red-800' />,
    },
    {
      count: `${metrics[0].success_rate}%`,
      percentage: '',
      css: 'bg-yellow-100 ',
      border: 'border-yellow-500',
      title: 'Approved Rate',
      icon: <FaChartLine className='text-[18px] text-yellow-800' />,
    },
  ];

  return (
    <div>
    </div>
  );
};

export default Stats;