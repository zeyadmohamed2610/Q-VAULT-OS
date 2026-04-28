import subprocess

def test_wifi():
    result = subprocess.run(["netsh", "wlan", "show", "networks", "mode=bssid"], capture_output=True, text=True)
    output = result.stdout
    networks = []
    lines = output.split('\n')
    current_net = None
    
    for line in lines:
        line = line.strip()
        if line.startswith("SSID"):
            if current_net: networks.append(current_net)
            # Try to catch name after first colon
            parts = line.split(":", 1)
            if len(parts) > 1:
                name = parts[1].strip()
                if not name: name = "[Hidden Network]"
                current_net = {"name": name, "strength": "0%", "secure": True}
        elif "Authentication" in line and current_net:
            if "Open" in line: current_net["secure"] = False
        elif "Signal" in line and current_net:
            sig = line.split(":", 1)[1].strip().replace("%", "")
            current_net["strength"] = f"{sig}%"
            
    if current_net: networks.append(current_net)
    
    print(f"Total found: {len(networks)}")
    for n in networks[:5]:
        print(f"- {n['name']} ({n['strength']})")

if __name__ == "__main__":
    test_wifi()
