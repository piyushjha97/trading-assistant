"use client";

import { Activity, LoaderCircle } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { marketDate, marketTime, price, quantity, type Candle, type Interval } from "../lib/market";

const padding = { top: 12, right: 64, bottom: 25, left: 12 };

export function PriceChart({
  candles,
  interval,
  loading,
  error,
}: {
  candles: Candle[];
  interval: Interval;
  loading: boolean;
  error?: string;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const selected = hover === null ? candles.at(-1) : candles[hover] ?? candles.at(-1);
  const range = useMemo(() => {
    let high = -Infinity;
    let low = Infinity;
    let volume = 0;
    for (const bar of candles) {
      high = Math.max(high, Number(bar.high));
      low = Math.min(low, Number(bar.low));
      volume = Math.max(volume, bar.volume);
    }
    const margin = Math.max((high - low) * 0.08, high * 0.001);
    return { high: high + margin, low: low - margin, volume };
  }, [candles]);

  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      setSize({ width: entry.contentRect.width, height: entry.contentRect.height });
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [candles.length]);

  useEffect(() => {
    const element = canvas.current;
    const context = element?.getContext("2d");
    const { width, height } = size;
    if (!element || !context || width < 100 || height < 80 || !candles.length) return;
    const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    element.width = Math.round(width * pixelRatio);
    element.height = Math.round(height * pixelRatio);
    context.scale(pixelRatio, pixelRatio);
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = (height - padding.bottom - padding.top) * 0.8;
    const slot = chartWidth / candles.length;
    const bodyWidth = Math.max(1, Math.min(12, slot * 0.64));
    const bottom = height - padding.bottom;
    const xAt = (index: number) => padding.left + (index + 0.5) * slot;
    const yAt = (value: number) => padding.top + (range.high - value) / (range.high - range.low) * chartHeight;

    context.font = "11px system-ui";
    context.textBaseline = "middle";
    for (let line = 0; line <= 4; line++) {
      const y = padding.top + chartHeight * line / 4;
      context.strokeStyle = "#253632";
      context.beginPath();
      context.moveTo(padding.left, y);
      context.lineTo(width - padding.right, y);
      context.stroke();
      context.fillStyle = "#a0b1ac";
      context.fillText(price(range.high - (range.high - range.low) * line / 4), width - padding.right + 8, y);
    }

    for (let index = 0; index < candles.length; index++) {
      const bar = candles[index];
      const x = xAt(index);
      const open = Number(bar.open);
      const close = Number(bar.close);
      context.fillStyle = close >= open ? "#81dfbb" : "#ee9f9f";
      context.strokeStyle = context.fillStyle;
      context.beginPath();
      context.moveTo(x, yAt(Number(bar.high)));
      context.lineTo(x, yAt(Number(bar.low)));
      context.stroke();
      context.fillRect(x - bodyWidth / 2, Math.min(yAt(open), yAt(close)), bodyWidth, Math.max(1, Math.abs(yAt(open) - yAt(close))));
      if (range.volume > 0) {
        const volumeHeight = bar.volume / range.volume * chartHeight * 0.17;
        context.globalAlpha = 0.4;
        context.fillRect(x - bodyWidth / 2, bottom - volumeHeight, bodyWidth, volumeHeight);
        context.globalAlpha = 1;
      }
    }

    const labels = Math.min(candles.length, width > 500 ? 5 : 3);
    context.fillStyle = "#a0b1ac";
    for (let point = 0; point < labels; point++) {
      const item = labels === 1 ? 0 : Math.round((candles.length - 1) * point / (labels - 1));
      const bar = candles[item];
      const label = interval === "day" || point === 0 ? marketDate(bar.timestamp) : marketTime(bar.timestamp);
      const x = Math.min(width - padding.right - context.measureText(label).width, Math.max(padding.left, xAt(item) - 14));
      context.fillText(label, x, height - 10);
    }

    if (hover !== null && candles[hover]) {
      context.strokeStyle = "#a6efd0";
      context.setLineDash([3, 4]);
      context.beginPath();
      context.moveTo(xAt(hover), padding.top);
      context.lineTo(xAt(hover), bottom);
      context.stroke();
    }
  }, [candles, hover, interval, range, size]);

  function updateHover(event: PointerEvent<HTMLCanvasElement>) {
    const bounds = event.currentTarget.getBoundingClientRect();
    const point = (event.clientX - bounds.left - padding.left) / (bounds.width - padding.left - padding.right);
    setHover(Math.min(candles.length - 1, Math.max(0, Math.floor(point * candles.length))));
  }

  function onChartKey(event: KeyboardEvent<HTMLCanvasElement>) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const step = event.key === "ArrowLeft" ? -1 : 1;
    setHover((index) => Math.max(0, Math.min(candles.length - 1, (index ?? candles.length - 1) + step)));
  }

  if (!candles.length) {
    const EmptyIcon = loading ? LoaderCircle : Activity;
    return (
      <div className="chart-empty">
        <div className="chart-empty-inner">
          <span className="chart-empty-icon"><EmptyIcon className={loading ? "spin" : undefined} size={24} /></span>
          <strong>{loading ? "Fetching candles" : error ? "Chart unavailable" : "No candles loaded"}</strong>
          <p>{loading ? "Waiting for the Kite market data feed." : error ?? "Load market data to see price and volume for this interval."}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chart-loaded">
      <dl className="chart-readout">
        <div><dt>Bar start</dt><dd>{selected ? marketDate(selected.timestamp) + (interval === "day" ? "" : " · " + marketTime(selected.timestamp)) : "—"}</dd></div>
        <div><dt>O</dt><dd>{price(selected?.open)}</dd></div>
        <div><dt>H</dt><dd>{price(selected?.high)}</dd></div>
        <div><dt>L</dt><dd>{price(selected?.low)}</dd></div>
        <div><dt>C</dt><dd>{price(selected?.close)}</dd></div>
        <div><dt>Vol</dt><dd>{quantity(selected?.volume)}</dd></div>
      </dl>
      <canvas
        ref={canvas}
        className="price-canvas"
        tabIndex={0}
        aria-label="Candlestick chart. Use the left and right arrow keys to inspect bars."
        onPointerMove={updateHover}
        onPointerLeave={() => setHover(null)}
        onKeyDown={onChartKey}
      />
    </div>
  );
}
