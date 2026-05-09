// ═══════════════════════════════════════════════════════════════
// WEBGL FALLBACK — Phase XIX Hardening
// Shown when the browser fails to create a WebGL context.
// Cold, institutional, authoritative maintenance state.
// ═══════════════════════════════════════════════════════════════

'use client';

export function WebGLFallback({ reason }: { reason?: string }) {
  return (
    <div className="fixed inset-0 z-[1000] bg-black flex items-center justify-center p-12 font-mono text-white/80">
      <div className="max-w-2xl w-full border border-white/10 p-8 relative overflow-hidden">
        {/* Subtle Background Signal */}
        <div className="absolute inset-0 opacity-[0.02] bg-[radial-gradient(circle,rgba(255,255,255,0.1)_1px,transparent_1px)] bg-[size:20px_20px]" />
        
        <div className="relative">
          <div className="text-[10px] tracking-[0.5em] text-white/20 mb-8">
            SOVEREIGN_INFRASTRUCTURE_AUTHORITY // ALERT
          </div>
          
          <h1 className="text-[24px] font-light tracking-tight mb-4">
            VISUAL_LAYER_OFFLINE
          </h1>
          
          <p className="text-[12px] leading-relaxed text-white/40 mb-8 max-w-lg">
            The Q-VAULT high-fidelity visualization layer requires a valid WebGL2 context to maintain 
            institutional render integrity. Your current hardware or environment is reporting an 
            interdiction in GPU context creation.
          </p>
          
          <div className="space-y-2 border-t border-white/5 pt-6">
            <div className="flex justify-between text-[9px] tracking-widest">
              <span className="text-white/20">ERROR_CODE</span>
              <span className="text-white/60">WEBGL_CONTEXT_REJECTED</span>
            </div>
            <div className="flex justify-between text-[9px] tracking-widest">
              <span className="text-white/20">SYSTEM_REASON</span>
              <span className="text-white/60 truncate ml-4">{reason || 'HARDWARE_ACCELERATION_DISABLED'}</span>
            </div>
            <div className="flex justify-between text-[9px] tracking-widest">
              <span className="text-white/20">STATE</span>
              <span className="text-white/60">DEGRADED_OPERATIONS</span>
            </div>
          </div>
          
          <div className="mt-12 text-[8px] text-white/10 uppercase tracking-[0.4em]">
            SYSTEM_STATUS: ACCESS_RESTRICTED // REQUIRES_VALID_RENDER_CONTEXT
          </div>
        </div>

        {/* Institutional corner markers */}
        <div className="absolute top-0 left-0 w-8 h-8 border-l border-t border-white/20" />
        <div className="absolute top-0 right-0 w-8 h-8 border-r border-t border-white/20" />
        <div className="absolute bottom-0 left-0 w-8 h-8 border-l border-b border-white/20" />
        <div className="absolute bottom-0 right-0 w-8 h-8 border-r border-b border-white/20" />
      </div>
    </div>
  );
}

export function isWebGLAvailable() {
  try {
    const canvas = document.createElement('canvas');
    return !!(
      window.WebGLRenderingContext &&
      (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
    );
  } catch (e) {
    return false;
  }
}
