'use client';
import { useAppStore } from '../store/useAppStore';
export default function SettingsPanel() { const { settings, setSettings } = useAppStore(); return <section className='card grid'><h3>Settings</h3><label>Default README length</label><select className='input' value={settings.length} onChange={(e)=>setSettings({length:e.target.value})}><option>Short</option><option>Medium</option><option>Detailed</option></select></section>; }
