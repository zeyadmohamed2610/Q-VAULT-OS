import psutil
import time
import sys
import os

def monitor_process(pid, duration=15):
    print(f"[*] Monitoring PID {pid} for {duration}s...")
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        print(f"[!] Process {pid} not found.")
        return

    start_time = time.time()
    violations = []
    
    while time.time() - start_time < duration:
        if not proc.is_running():
            print("[!] Process terminated.")
            break
            
        connections = proc.connections(kind='inet')
        for conn in connections:
            # Ignore loopback/local connections
            if conn.raddr and conn.raddr.ip not in ('127.0.0.1', '::1', '0.0.0.0'):
                msg = f"[!] OUTBOUND DETECTED: {conn.laddr} -> {conn.raddr} (Status: {conn.status})"
                if msg not in violations:
                    violations.append(msg)
                    print(msg)
        
        time.sleep(0.5)

    if not violations:
        print("\n[SUCCESS] NETWORK AUDIT: CLEAN. No external outbound requests detected.")
    else:
        print(f"\n[FAILURE] NETWORK AUDIT: FAILED. {len(violations)} external connections detected.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python network_audit.py <PID>")
        sys.exit(1)
    
    monitor_process(int(sys.argv[1]))
