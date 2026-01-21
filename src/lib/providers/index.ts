import { MusicProvider } from '@/types/music';
import { GequbaoProvider } from './impl/gequbao';
import { QQMp3Provider } from './impl/qqmp3';
import { MiguProvider } from './impl/migu';

const providers: Record<string, MusicProvider> = {
  gequbao: new GequbaoProvider(),
  qqmp3: new QQMp3Provider(),
  migu: new MiguProvider(),
};

export function getProvider(name: string = 'gequbao'): MusicProvider {
  return providers[name] || providers['gequbao'];
}

export function getAllProviders(): MusicProvider[] {
  return Object.values(providers);
}
