import React, { useState } from 'react';
import { Palette, Sparkles, Utensils, Music } from 'lucide-react';


export default function CreativeSection({ theme, decorations, catering, entertainment }) {
  const [copiedHex, setCopiedHex] = useState(null);

  const copyToClipboard = (hex) => {
    navigator.clipboard?.writeText(hex);
    setCopiedHex(hex);
    setTimeout(() => setCopiedHex(null), 1500);
  };

  const palette = theme?.color_palette || ['#F8F9FA', '#E9D8A6', '#EE9B00', '#005F73', '#0A9396'];
  const decorList = decorations || [];
  const caterList = catering || [];
  const musicList = entertainment || [];

  return (
    <section id="creative-section" className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl backdrop-blur-md">
      {/* Header */}
      <div className="pb-6 border-b border-slate-800/80">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Palette className="h-4 w-4" />
          </span>
          <h3 className="text-xl font-bold text-white tracking-tight">Aesthetic Themes & Creative Directives</h3>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          Coordinated color harmony, decorative installations, culinary spreads, and sensory entertainment.
        </p>
      </div>

      {/* Recommended Theme Card */}
      <div className="mt-6 rounded-xl border border-slate-800/80 bg-slate-950/60 p-5">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-slate-800/60">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">
              Curated Theme Concept
            </span>
            <h4 className="text-lg font-bold text-white mt-0.5">
              {theme?.name || 'Artisanal Elegance'}
            </h4>
            <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
              {theme?.description || 'A balanced palette and spatial aesthetic curated for this celebration.'}
            </p>
          </div>

          {/* Color Palette Swatches */}
          <div className="flex flex-col items-start md:items-end">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              Color Palette (Click to Copy)
            </span>
            <div className="flex items-center gap-2">
              {palette.map((color, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => copyToClipboard(color)}
                  className="group relative flex flex-col items-center"
                  title={`Copy hex ${color}`}
                >
                  <span
                    className="h-8 w-8 rounded-lg shadow-md border border-white/20 transition-transform group-hover:scale-110 active:scale-95"
                    style={{ backgroundColor: color }}
                  />
                  <span className="mt-1 font-mono text-[9px] text-slate-400 uppercase">
                    {copiedHex === color ? 'Copied!' : color}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* 3 Columns: Decor, Catering, Entertainment */}
        <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-3">
          {/* Decorations */}
          <div className="rounded-xl border border-slate-800/80 bg-slate-900/50 p-4">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-800/60 text-indigo-400 font-semibold text-xs">
              <Sparkles className="h-4 w-4" />
              <span>Decor & Floral Scenography</span>
            </div>
            <ul className="mt-3 space-y-2 text-xs text-slate-300">
              {decorList.map((item, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 shrink-0 mt-1.5" />
                  <span className="leading-snug">{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Catering */}
          <div className="rounded-xl border border-slate-800/80 bg-slate-900/50 p-4">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-800/60 text-amber-400 font-semibold text-xs">
              <Utensils className="h-4 w-4" />
              <span>Culinary & Hospitality</span>
            </div>
            <ul className="mt-3 space-y-2 text-xs text-slate-300">
              {caterList.map((item, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400 shrink-0 mt-1.5" />
                  <span className="leading-snug">{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Entertainment */}
          <div className="rounded-xl border border-slate-800/80 bg-slate-900/50 p-4">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-800/60 text-emerald-400 font-semibold text-xs">
              <Music className="h-4 w-4" />
              <span>Music, Sound & Experiences</span>
            </div>
            <ul className="mt-3 space-y-2 text-xs text-slate-300">
              {musicList.map((item, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shrink-0 mt-1.5" />
                  <span className="leading-snug">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
