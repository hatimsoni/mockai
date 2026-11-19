"use client";

// Chart rules (see dataviz guidance): one y-axis per chart (never dual-axis), thin 2px lines,
// >=8px markers, recessive grid, a legend for >=2 series plus direct end labels, hover tooltips,
// categorical colors assigned in a fixed order (validated reference palette), text in ink colors.
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export const SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]; // slots 1-4, fixed order
const INK = { secondary: "#52514e", muted: "#8a8984", grid: "#e7e6e2" };

const axis = { stroke: INK.muted, fontSize: 12, tickLine: false, axisLine: false } as const;
const tooltipStyle = { borderRadius: 8, border: `1px solid ${INK.grid}`, fontSize: 12 };

export type Point = Record<string, string | number | null>;

export function TrendChart({
  data,
  series,
  domain,
  unit = "",
  height = 240,
}: {
  data: Point[];
  series: { key: string; label: string; dashed?: boolean }[];
  domain?: [number, number];
  unit?: string;
  height?: number;
}) {
  const many = series.length >= 2;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: many ? 72 : 16, bottom: 0, left: -12 }}>
        <CartesianGrid stroke={INK.grid} vertical={false} />
        <XAxis dataKey="label" {...axis} />
        <YAxis domain={domain ?? ["auto", "auto"]} {...axis} unit={unit} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: INK.muted, strokeDasharray: "3 3" }} />
        {many && <Legend iconType="plainline" wrapperStyle={{ fontSize: 12, color: INK.secondary }} />}
        {series.map((s, i) => (
          <Line
            key={s.key}
            dataKey={s.key}
            name={s.label}
            stroke={SERIES[i]}
            strokeWidth={2}
            strokeDasharray={s.dashed ? "5 4" : undefined}
            dot={{ r: 4, strokeWidth: 2, stroke: "#fff", fill: SERIES[i] }}
            activeDot={{ r: 6, stroke: "#fff", strokeWidth: 2 }}
            connectNulls
            isAnimationActive={false}
            // direct label on the last point only (identity never relies on color alone)
            label={
              many
                ? (props: { index?: number; x?: number | string; y?: number | string }) =>
                    props.index === data.length - 1 ? (
                      <text x={Number(props.x) + 8} y={Number(props.y) + 4} fontSize={11} fill={INK.secondary}>
                        {s.label}
                      </text>
                    ) : null
                : undefined
            }
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function HBarChart({
  data,
  valueKey,
  labelKey,
  domain,
  height = 220,
}: {
  data: Point[];
  valueKey: string;
  labelKey: string;
  domain?: [number, number];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 8 }} barCategoryGap={6}>
        <CartesianGrid stroke={INK.grid} horizontal={false} />
        <XAxis type="number" domain={domain ?? [0, "auto"]} {...axis} />
        <YAxis type="category" dataKey={labelKey} width={120} {...axis} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#f4f3f0" }} />
        <Bar dataKey={valueKey} fill={SERIES[0]} radius={[0, 4, 4, 0]} maxBarSize={18} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}
