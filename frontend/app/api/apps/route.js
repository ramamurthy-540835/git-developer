import { NextResponse } from 'next/server';

export async function GET() {
  const apps = [
    {
      name: 'vbc_dashboard',
      url: 'https://vbc-dashboard-1035117862188.us-central1.run.app',
      description: 'Value Based Care dashboard with risk stratification and care insights',
    },
    {
      name: 'weathernext_dashboard',
      url: 'https://weathernext-dashboard-1035117862188.us-central1.run.app',
      description: 'AI weather forecasting and climate intelligence platform',
    },
    {
      name: 'adept_healthcare',
      url: 'https://adept-healthcare-vbc-pa-frontend-1035117862188.us-central1.run.app',
      description: 'Prior authorization + VBC healthcare platform',
    },
    {
      name: 'dataeng_console',
      url: 'https://dataeng-console-1035117862188.us-central1.run.app',
      description: 'Data engineering pipelines and analytics console',
    },
    {
      name: 'ctopteam_frontend',
      url: 'https://ctopteam-frontend-1035117862188.us-central1.run.app',
      description: 'GenAI + modernization platform UI',
    },
  ];
  return NextResponse.json(apps);
}
