import os
import subprocess
import logging

logger = logging.getLogger(__name__)

class SystemControlHelper:
    @staticmethod
    def set_volume(percent):
        """Sets system volume (0-100) using a faster PowerShell snippet."""
        try:
            # We use a more direct PS call. To avoid 'slowness', we rely on the UI debouncing.
            # This snippet uses the Shell.Application COM object which is faster than SendKeys loops.
            # However, for 'real' control without external libs, SendKeys is the most 'standard' hack.
            # Let's use a more efficient SendKeys approach by calculating the delta.
            ps_script = f"""
            $wsh = New-Object -ComObject WScript.Shell
            # Target is {percent}, we assume we don't know current, so we go to 0 then up.
            # Optimized: Just set the percentage if possible.
            # On Windows 10/11, we can use a small C# snippet via PS for instant volume.
            Add-Type -TypeDefinition @'
            using System.Runtime.InteropServices;
            [Guid("5CDF2C82-1541-4993-93A6-978D1494C25A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IAudioEndpointVolume {{
                int f(); int g(); int h(); int i();
                int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
            }}
            [Guid("D6660639-165F-4560-AD82-974F02966A4D"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IMMDevice {{ int Activate(ref System.Guid id, int cls, System.IntPtr config, out IAudioEndpointVolume interfacePointer); }}
            [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IMMDeviceEnumerator {{ int f(); int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint); }}
            [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorComObject {{ }}
            public class Vol {{
                public static void Set(float v) {{
                    IMMDeviceEnumerator enumerator = (IMMDeviceEnumerator)new MMDeviceEnumeratorComObject();
                    IMMDevice device; enumerator.GetDefaultAudioEndpoint(0, 1, out device);
                    IAudioEndpointVolume volume; var iid = new System.Guid("5CDF2C82-1541-4993-93A6-978D1494C25A");
                    device.Activate(ref iid, 1, System.IntPtr.Zero, out volume);
                    volume.SetMasterVolumeLevelScalar(v, System.Guid.Empty);
                }}
            }}
'@
            [Vol]::Set({percent}/100.0)
            """
            subprocess.Popen(["powershell", "-Command", ps_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")

    @staticmethod
    def get_wifi_networks():
        """Scans for WiFi networks with robust regex parsing."""
        try:
            import re
            # Use default show networks which is faster for discovery
            result = subprocess.run(["netsh", "wlan", "show", "networks"], capture_output=True, text=True)
            output = result.stdout
            
            networks = []
            # Regex to match SSID lines and capture the name
            # Format: SSID X : NAME
            ssid_matches = re.findall(r"SSID \d+ : (.*)", output)
            
            # Since we only get names from findall, we'll do a slightly more complex split if we want encryption
            ssid_blocks = re.split(r"SSID \d+ : ", output)
            for block in ssid_blocks[1:]: # Skip text before first SSID
                lines = block.split('\n')
                name = lines[0].strip()
                if not name: name = "[Hidden Network]"
                
                secure = True
                if any("Open" in l for l in lines): secure = False
                
                networks.append({"name": name, "strength": "75%", "secure": secure})
            
            # Deduplicate by name
            seen = set()
            unique_nets = []
            for n in networks:
                if n['name'] not in seen:
                    unique_nets.append(n)
                    seen.add(n['name'])
                    
            return unique_nets if unique_nets else [{"name": "No Networks Found", "strength": "0%", "secure": False}]
        except Exception as e:
            logger.error(f"WiFi Scan failed: {e}")
            return []
        except Exception as e:
            logger.error(f"WiFi Scan failed: {e}")
            return []

    @staticmethod
    def power_action(action):
        """Shutdown, Restart, or Sleep."""
        try:
            if action == "shutdown":
                os.system("shutdown /s /t 0")
            elif action == "restart":
                os.system("shutdown /r /t 0")
            elif action == "sleep":
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        except Exception as e:
            logger.error(f"Power action {action} failed: {e}")

    @staticmethod
    def set_airplane_mode(enabled):
        """Enables/Disables WiFi and Bluetooth via netsh and PowerShell."""
        try:
            if enabled:
                subprocess.Popen(["powershell", "-Command", "Disable-NetAdapter -Name '*' -Confirm:$false"], stdout=subprocess.DEVNULL)
                subprocess.Popen(["powershell", "-Command", "Stop-Service -Name bthserv -Force"], stdout=subprocess.DEVNULL)
            else:
                subprocess.Popen(["powershell", "-Command", "Enable-NetAdapter -Name '*' -Confirm:$false"], stdout=subprocess.DEVNULL)
                subprocess.Popen(["powershell", "-Command", "Start-Service -Name bthserv"], stdout=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Airplane mode toggle failed: {e}")
