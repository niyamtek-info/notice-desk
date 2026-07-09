"use client"
import BankList from '@/components/pages/banks'
import usePageTitle from '@/hooks/usePageTitle';
import React from 'react'

export default function page() {
  usePageTitle('Niyamtek');
  return (
    <BankList />
  )
}
