import { headers } from 'next/headers';
import { App } from '@/components/app/app';
import { getAppConfig } from '@/lib/utils';

export default async function Page() {
  const hdrs = await headers();
  const appConfig = await getAppConfig(hdrs);

  return (
    <>
      {/* ⚛️ START: PW-Inspired Tutor Badge ⚛️ */}
      <style>{`
        @keyframes pulse-red {
          0% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7); }
          70% { box-shadow: 0 0 0 10px rgba(220, 38, 38, 0); }
          100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }
        }
      `}</style>

      <div style={{
        position: 'fixed',
        top: '24px',
        left: '24px',
        zIndex: 9999,
        background: '#1a1a1a', // PW Dark Grey
        borderLeft: '5px solid #DC2626', // PW Red Accent
        padding: '16px 24px',
        borderRadius: '8px',
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        boxShadow: '0 10px 30px rgba(0, 0, 0, 0.5)',
        fontFamily: 'sans-serif',
        color: 'white'
      }}>
        
        {/* Live Status */}
        <div style={{
          width: '12px',
          height: '12px',
          background: '#DC2626',
          borderRadius: '50%',
          animation: 'pulse-red 2s infinite'
        }}></div>

        {/* Text Info */}
        <div>
          <div style={{ 
            fontSize: '18px', 
            fontWeight: '800', 
            textTransform: 'uppercase',
            letterSpacing: '1px'
          }}>
            AI Tutor <span style={{color: '#DC2626'}}>Live</span>
          </div>
          
          <div style={{ 
            fontSize: '12px', 
            color: '#fbbf24', // Gold/Yellow for "Premium" feel
            marginTop: '4px',
            fontWeight: '600'
          }}>
            Active Recall Coach • Day 4
          </div>
        </div>
      </div>
      {/* ⚛️ END Badge ⚛️ */}

      <App appConfig={appConfig} />
    </>
  );
}