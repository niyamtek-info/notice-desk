"use client"
import Template from '@/components/pages/template'
import usePageTitle from '@/hooks/usePageTitle';
import React from 'react'

export default function page() {
  usePageTitle('Niyamtek');
  return (
    <>
    <Template />
    </>
  )
}
