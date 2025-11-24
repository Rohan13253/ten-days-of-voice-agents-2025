import { headers } from 'next/headers';
import { App } from '@/components/app/app';
import { getAppConfig } from '@/lib/utils';

export default async function Page() {
  const hdrs = await headers();
  const appConfig = await getAppConfig(hdrs);

  return (
    <>
      {/* 🌿 START: Premium Wellness Badge 🌿 */}
      <style>{`
        @keyframes sway {
          0% { transform: rotate(-10deg); }
          50% { transform: rotate(10deg); }
          100% { transform: rotate(-10deg); }
        }
        @keyframes blink {
          0% { opacity: 0.4; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.2); }
          100% { opacity: 0.4; transform: scale(1); }
        }
        @keyframes slideIn {
          from { transform: translateY(-20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
      `}</style>

      <div style={{
        position: 'fixed',
        top: '24px',
        left: '24px',
        zIndex: 9999,
        // Glassmorphism Effect
        background: 'rgba(255, 255, 255, 0.85)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)', // For Safari
        border: '1px solid rgba(255, 255, 255, 0.5)',
        
        padding: '14px 22px',
        borderRadius: '20px',
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        
        // Premium Shadow
        boxShadow: '0 10px 40px -10px rgba(0,0,0,0.15), 0 0 0 1px rgba(255,255,255,0.2)',
        color: '#1e293b',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Inter", sans-serif',
        animation: 'slideIn 0.6s ease-out'
      }}>
        
        {/* Animated Icon Container */}
        <div style={{ 
          fontSize: '32px', 
          filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.1))',
          animation: 'sway 4s ease-in-out infinite' 
        }}>
          🌿
        </div>

        {/* Divider Line */}
        <div style={{ width: '1px', height: '30px', background: '#e2e8f0' }}></div>

        {/* Text Info */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <div style={{ 
            fontSize: '15px', 
            fontWeight: '800', 
            color: '#047857', // Deep Emerald
            letterSpacing: '-0.2px'
          }}>
            Wellness Companion
          </div>
          
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '6px',
            fontSize: '11px', 
            fontWeight: '600',
            color: '#64748b',
            textTransform: 'uppercase',
            letterSpacing: '0.5px'
          }}>
            {/* Pulsing Status Dot */}
            <span style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: '#10b981',
              animation: 'blink 2s infinite'
            }}></span>
            Memory Active • Day 3
          </div>
        </div>
      </div>
      {/* 🌿 END Badge 🌿 */}

      <App appConfig={appConfig} />
    </>
  );
}