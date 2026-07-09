'use client';

import React, { useEffect, useState } from 'react';
import { Button, Modal } from 'antd';
import { MenuUnfoldOutlined, MenuFoldOutlined } from '@ant-design/icons';
import { RiMenuFoldFill, RiMenuUnfoldFill } from "react-icons/ri";
import { DownOutlined } from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { Dropdown, Space, message } from 'antd';
import { FaRegUser, FaSearch } from "react-icons/fa";
import { MdLogout } from "react-icons/md";
import { RiArrowDropDownLine } from "react-icons/ri";
import { IoSettingsOutline } from "react-icons/io5";
import { useBank } from '@/context/BankContext';
import { useTitle } from '@/context/TitleContext';
import { useParams, usePathname, useSearchParams, useRouter } from "next/navigation";
import Link from 'next/link';
import { Select } from "antd";
import { logoutUser } from '@/src/utils/auth';
import logo from "@/images/niyamtek.png"
import Image from 'next/image';


interface HeaderSectionProps {
  collapsed: boolean;
  collapsedWidth: number;
  toggleCollapsed: () => void;
}

const items: MenuProps['items'] = [
  // {
  //   label: (
  //     <div className='flex items-center gap-2'>
  //       <FaRegUser className='text-primary-500 min-w-[17px]' />
  //       <span>Profile</span>
  //     </div>
  //   ),
  //   key: '0',
  // },
  // {
  //   label: (
  //     <div className='flex items-center gap-2'>
  //       <IoSettingsOutline className='text-primary-500 text-[16px] min-w-[17px]' />
  //       <span>Settings</span>
  //     </div>
  //   ),
  //   key: '2',
  // },
  // {
  //   type: 'divider',
  // },
  // {
  //   label: (
  //     <div className='flex items-center gap-2'>
  //       <MdLogout className='text-[16px] text-red-500' />
  //       <span>Logout</span>
  //     </div>
  //   ),
  //   key: '3',
  // }
];
const HeaderSection: React.FC<HeaderSectionProps> = ({ collapsed, toggleCollapsed, collapsedWidth }) => {

  const { title } = useTitle();
  const { selectedBank, setSelectedBank } = useBank();

  const params = useParams();
  const pathname = usePathname();

  // only show Application ID if current path starts with /overview or /application-details
  const showAppId = (pathname.startsWith("/overview/") || pathname.startsWith("/application-details/")) && params?.id;
  const appId = showAppId ? params.id : null;

  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [searchValue, setSearchValue] = useState<string | undefined>(undefined);
  const [confirmVisible,setConfirmVisible] = useState<boolean>(false)

  const onChange = (value: string) => {
    setOpen(false);
    setSearchValue(undefined);
    router.push(`/overview`);

  };

  const onSearch = (value: string) => {
    if (value) {
      setOpen(true); // 🔹 Open dropdown as soon as user types
    } else {
      setOpen(false); // close if input is cleared
    }
  };


  const searchParams = useSearchParams();
  const idFromUrl = searchParams.get("id");
  const [latestId, setLatestId] = useState<string | null>(null);
  const pathName = usePathname();


  useEffect(() => {
    if (idFromUrl) {
      setLatestId(idFromUrl);
      localStorage.setItem("applicationNumber", idFromUrl);
    }
  }, [idFromUrl]);

  useEffect(() => {
    if (!idFromUrl) {
      const savedId = localStorage.getItem("applicationNumber");
      if (savedId) setLatestId(savedId);
    }
  }, [idFromUrl]);



  const handleMenuClick = () => {
    // if (e.key === '3') {
      // message.success("Logged out successfully");
      setConfirmVisible(true)
    // }
  };

  return (
    <>
    <div className={`flex justify-between items-center w-[100%] ml-${collapsedWidth}px`}>
      {pathName !== "/dashboard" ? 
      <Link href={"/dashboard"} className='flex items-center gap-1'>
        <Image alt="company_logo" src={logo} width={100} height={100} />
      </Link>
      :
      <div className='flex items-center gap-1'>
        <Image alt="company_logo" src={logo} width={100} height={100} />
      </div>
      }
      {/* <div className='flex items-center'>

        {appId && <div className='my-auto  mr-4'>

          <p className="text-gray-500  px-3 py-2 rounded-lg">
            <span className="font-semibold text-gray-700">Application ID: </span>
            <span className="text-primary-500 font-semibold">
              {appId ?? "—"}
            </span>
          </p>
        </div>}

        <Link href="/dashboard" className={`mr-4  ${pathname == "/dashboard" ? "!text-primary pointer-events-none cursor-not-allowed" :"!text-black"} `}>Dashboard</Link>
        <Link href={`/banks`} className={`!mr-4 ${pathname == "/banks" ? "!text-primary pointer-events-none cursor-not-allowed" :"!text-black"} `}>Bank</Link>
        <Link href={`/template`} className={`!mr-4 ${pathname == "/template" ? "!text-primary pointer-events-none cursor-not-allowed" :"!text-black"} `}>Template</Link>

        <Dropdown menu={{ items, onClick: handleMenuClick }} trigger={['click']}>
          <div className='my-auto'>
            <button type='button' className='flex item-center cursor-pointer bg-gray-100 p-2 pr-1 rounded-full' onClick={(e) => e.preventDefault()}>
              <FaRegUser />
              <RiArrowDropDownLine className='text-[17px]' />
            </button>
          </div>
        </Dropdown>
      </div> */}

      <div className="flex items-center">

        {appId && (
          <div className="my-auto mr-6">
            <p className="text-gray-500 px-3 py-2 rounded-lg">
              <span className="font-semibold text-gray-700">Application ID: </span>
              <span className="text-primary-500 font-semibold">
                {appId ?? "—"}
              </span>
            </p>
          </div>
        )}

        {/* Dashboard */}
        <Link
          href="/dashboard"
          className={`relative mr-6 font-semibold transition-colors
    ${pathname === "/dashboard"
              ? "text-primary pointer-events-none after:w-full"
              : "!text-gray-600 hover:text-primary after:w-0 hover:after:w-full"
            }
    after:content-[''] after:absolute after:left-0 after:bottom-[13px]
    after:h-[3px] after:bg-primary after:transition-all after:duration-300`}
        >
          Dashboard
        </Link>

        {/* Bank */}
        <Link
          href="/clients"
          className={`relative mr-6 font-semibold transition-colors
    ${pathname === "/clients"
              ? "text-primary pointer-events-none after:w-full"
              : "!text-gray-600 hover:text-primary after:w-0 hover:after:w-full"
            }
    after:content-[''] after:absolute after:left-0 after:bottom-[13px]
    after:h-[3px] after:bg-primary after:transition-all after:duration-300`}
        >
          Client
        </Link>

        {/* Template */}
        <Link
          href="/template"
          className={`relative mr-6 font-semibold transition-colors
    ${pathname === "/template"
              ? "text-primary pointer-events-none after:w-full"
              : "!text-gray-600 hover:text-primary after:w-0 hover:after:w-full"
            }
    after:content-[''] after:absolute after:left-0 after:bottom-[13px]
    after:h-[3px] after:bg-primary after:transition-all after:duration-300`}
        >
          Template
        </Link>

        <div onClick={handleMenuClick} className='flex items-center gap-2 text-red-500 border border-red-400 cursor-pointer rounded-lg h-[30px] px-3 hover:bg-red-400 hover:text-white'>
         <MdLogout className='text-[16px]' />
         <span>Logout</span>
       </div>

        {/* User Dropdown */}
        {/* <Dropdown menu={{ items, onClick: handleMenuClick }} trigger={["click"]}>
          <div className="my-auto">
            <button
              type="button"
              className="flex items-center cursor-pointer bg-gray-100 p-2 pr-1 rounded-full"
              onClick={(e) => e.preventDefault()}
            >
              <FaRegUser /> */}
              {/* <RiArrowDropDownLine className="text-[17px]" /> */}
            {/* </button>
          </div>
        </Dropdown> */}
         

      </div>

    </div>

      {/* Confirmation Modal */}
      <Modal
        open={confirmVisible}
        onOk={() => {
         logoutUser();
        }}
        onCancel={() => setConfirmVisible(false)}
        okText="Logout"
        okType="danger"
        okButtonProps={{
          className: " hover:!text-white hover:!bg-[#ff4d4f] border-red-600",
        }}
        cancelText="Cancel"
        title="Are you sure?"
        zIndex={1100}
      >
        <p>Are you sure you want to log out?</p>
      </Modal> 
    </>
  );
};

export default HeaderSection;
