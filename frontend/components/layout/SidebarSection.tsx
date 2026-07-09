'use client';

import React from 'react';
import { Menu } from 'antd';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { RxDashboard } from 'react-icons/rx';
import { FaTasks } from 'react-icons/fa';
import { IoChatboxEllipsesOutline, IoPeopleOutline } from "react-icons/io5";
import { LuBookText } from 'react-icons/lu';

interface SidebarSectionProps {
  collapsed: boolean;
}

const SidebarSection: React.FC<SidebarSectionProps> = ({ collapsed }) => {
  const pathname = usePathname();

  const pathToKey: Record<string, string> = {
    '/dashboard': '1',
  };

  return (
    <>

      <Menu
        mode="inline"
        selectedKeys={[pathToKey[pathname] ?? '']}
        className={`!border-none sidebar-menu !mt-4 ${collapsed ? 'collapsed' : ''}`}
        items={[
          {
            key: '1',
            icon: <RxDashboard className="!text-[18px]" />,
            label: collapsed ? null : <Link href="/dashboard">Dashboard</Link>,
          },
        ]}
      />
    </>
  );
};

export default SidebarSection;
