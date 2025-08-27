import dynamic from 'next/dynamic';
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

export interface ChartProps {
  data: any[];
  layout?: any;
}

export default function Chart({ data, layout }: ChartProps) {
  return <Plot data={data} layout={layout} />;
}
