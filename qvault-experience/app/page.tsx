'use client';

import dynamic from 'next/dynamic';

const ExperienceLayout = dynamic(
  () => import('@/components/experience/ExperienceLayout'),
  { ssr: false }
);

export default function HomePage() {
  return <ExperienceLayout />;
}
