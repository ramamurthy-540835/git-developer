import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

type Scene = {
  id: number;
  title: string;
  subtitle: string;
  bullets: string[];
  caption: string;
};

type Props = {
  plan: {video: {duration_s: number}; scenes: Scene[]};
  productName: string;
};

export const FourBeatScene: React.FC<Props> = ({plan, productName}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const scenes = plan?.scenes?.length ? plan.scenes : [{id: 1, title: 'Overview', subtitle: 'Product demo', bullets: ['Flow'], caption: 'Demo'}];
  const sceneFrames = Math.floor(durationInFrames / scenes.length);
  const idx = Math.min(scenes.length - 1, Math.floor(frame / sceneFrames));
  const s = scenes[idx];
  const local = frame - idx * sceneFrames;
  const titleY = spring({fps, frame: local, config: {damping: 18}}) * 30;
  const opacity = interpolate(local, [0, 12, sceneFrames - 12, sceneFrames], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const progress = ((idx + 1) / scenes.length) * 100;

  return (
    <AbsoluteFill style={{backgroundColor: '#101820', color: '#ECF3FF', fontFamily: 'Segoe UI, Arial, sans-serif', opacity, overflow: 'hidden'}}>
      <div style={{height: 96, background: '#1F2A3A', display: 'flex', alignItems: 'center', padding: '0 36px', fontSize: 34, fontWeight: 700}}>
        {productName}
      </div>
      <div style={{display: 'flex', flex: 1, padding: 64, gap: 48}}>
        <div style={{flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between'}}>
          <div>
            <div style={{fontSize: 52, fontWeight: 700, transform: `translateY(${titleY}px)`}}>{s.title}</div>
            <div style={{fontSize: 30, marginTop: 14, color: '#BBD4FF'}}>{s.subtitle}</div>
          </div>
          <div style={{fontSize: 28, background: 'rgba(0,0,0,0.45)', padding: '14px 18px', borderRadius: 12, wordBreak: 'break-word', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical'}}>
            {s.caption}
          </div>
        </div>
        <div style={{width: 760, background: 'rgba(0,0,0,0.45)', borderRadius: 20, padding: 30}}>
          <div style={{fontSize: 30, marginBottom: 16, color: '#8EC5FF'}}>Scene {idx + 1} / {scenes.length}</div>
          {s.bullets?.slice(0, 3).map((b, i) => (
            <div key={i} style={{fontSize: 34, margin: '16px 0'}}>• {b}</div>
          ))}
        </div>
      </div>
      <div style={{height: 12, background: '#24324A'}}>
        <div style={{height: '100%', width: `${progress}%`, background: '#8EC5FF'}} />
      </div>
    </AbsoluteFill>
  );
};

