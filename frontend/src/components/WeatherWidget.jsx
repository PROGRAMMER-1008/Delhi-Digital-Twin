import React from 'react';
import { Droplets, Wind, Eye, Thermometer } from 'lucide-react';

const WEATHER_ICONS = {
  Clear:        '☀️',
  Clouds:       '☁️',
  Rain:         '🌧️',
  Drizzle:      '🌦️',
  Thunderstorm: '⛈️',
  Snow:         '❄️',
  Mist:         '🌫️',
  Haze:         '🌫️',
  Fog:          '🌫️',
  Smoke:        '🌫️',
  Dust:         '💨',
  default:      '🌡️',
};

export default function WeatherWidget({ cityState }) {
  const w = cityState?.weather;
  if (!w) return (
    <div className="panel-section">
      <div className="section-title" style={{ marginBottom: 12 }}>Weather</div>
      <div className="empty-state" style={{ padding: 20 }}>
        <div className="empty-icon">🌡️</div>
        <div className="empty-text">Loading weather data…</div>
      </div>
    </div>
  );

  const icon = WEATHER_ICONS[w.condition] ?? WEATHER_ICONS.default;
  const humidColor = w.humidity > 80 ? 'var(--cyan)' : w.humidity > 60 ? 'var(--text-secondary)' : 'var(--text-muted)';

  return (
    <div className="panel-section">
      <div className="section-title" style={{ marginBottom: 12 }}>Live Weather — Delhi</div>

      <div className="weather-row">
        <div className="weather-icon">{icon}</div>
        <div>
          <div className="weather-temp">{Math.round(w.temperature)}°<span style={{ fontSize: 14, color: 'var(--text-muted)' }}>C</span></div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginTop: 2 }}>
            {w.condition}
          </div>
        </div>
        <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>FEELS</div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 700, color: 'var(--text-secondary)' }}>
            {Math.round(w.feels_like ?? w.temperature)}°
          </div>
        </div>
      </div>

      <div className="weather-details">
        <div className="weather-detail">
          <Droplets size={10} color={humidColor} />
          <span style={{ color: humidColor }}>{w.humidity}%</span>
          <span style={{ color: 'var(--text-muted)' }}>humidity</span>
        </div>
        <div className="weather-detail">
          <Wind size={10} color="var(--text-muted)" />
          <span>{w.wind_speed?.toFixed(1)} m/s</span>
        </div>
        <div className="weather-detail">
          <Eye size={10} color="var(--text-muted)" />
          <span>{w.visibility ? (w.visibility / 1000).toFixed(1) + ' km' : '—'}</span>
        </div>
        <div className="weather-detail">
          <Thermometer size={10} color="var(--text-muted)" />
          <span>{w.pressure ? w.pressure + ' hPa' : '—'}</span>
        </div>
      </div>

      {/* Rain impact note */}
      {(w.condition === 'Rain' || w.condition === 'Drizzle' || w.condition === 'Thunderstorm') && (
        <div style={{
          marginTop: 10,
          background: 'rgba(0,200,255,0.08)',
          border: '1px solid rgba(0,200,255,0.2)',
          borderRadius: 'var(--r-sm)',
          padding: '6px 10px',
          fontFamily: 'var(--font-mono)',
          fontSize: 9,
          color: 'var(--cyan)',
          letterSpacing: '0.06em',
        }}>
          ⚠ RAIN IMPACT — Traffic capacity reduced ~25%
        </div>
      )}
    </div>
  );
}
