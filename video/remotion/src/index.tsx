import React from 'react';
import {Composition} from 'remotion';
import {FourBeatScene} from './scenes/FourBeatScene';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Demo"
      component={FourBeatScene}
      durationInFrames={960}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{plan: {video: {duration_s: 32, fps: 30, resolution: '1080p', aspect: '16:9'}, scenes: []}, productName: 'Demo'}}
    />
  );
};

export default RemotionRoot;

