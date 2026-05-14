using System;
using System.IO;
using System.IO.Ports;
using System.Management;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Effects;
using System.Windows.Threading;
using Microsoft.Win32;
using System.Windows.Input;
using NBitcoin;

namespace PQC_Vault
{
    public partial class MainWindow : Window
    {
        private const string TargetHWID = "VID_1A86&PID_55D3";
        private string? _detectedComPort = null;
        private DispatcherTimer _detectionTimer = null!;
        private DispatcherTimer? _encryptionTimer;
        private string? _encryptingDrive;

        private int _overlayTicks = 0;
        private bool _overlayHidden = false;
        private Storyboard _pulseStoryboard = null!;

        public MainWindow()
        {
            InitializeComponent();
        }

        private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            if (e.ChangedButton == MouseButton.Left)
                this.DragMove();
        }

        private void CloseBtn_Click(object sender, RoutedEventArgs e)
        {
            this.Close();
        }

        private void MinimizeBtn_Click(object sender, RoutedEventArgs e)
        {
            this.WindowState = WindowState.Minimized;
        }

        private void Window_Loaded(object sender, RoutedEventArgs e)
        {
            this.Activate();
            this.Topmost = true;
            this.Topmost = false;
            this.Focus();

            _pulseStoryboard = (Storyboard)FindResource("PulseAnim");

            LoadBitLockerDrives();

            // Setup timer to continuously look for the ESP device
            _detectionTimer = new DispatcherTimer();
            _detectionTimer.Interval = TimeSpan.FromSeconds(1);
            _detectionTimer.Tick += DetectionTimer_Tick;
            _detectionTimer.Start();
            
            // Initial check
            _ = CheckForQVaultKeyAsync();
            UpdateOverlayText();
        }

        private bool _isDetecting = false;

        private async void DetectionTimer_Tick(object sender, EventArgs e)
        {
            if (_isDetecting) return;
            _isDetecting = true;

            try
            {
                if (!_overlayHidden)
                {
                    _overlayTicks++;
                    UpdateOverlayText();

                    if (_overlayTicks >= 10)
                    {
                        HideOverlay();
                    }
                }

                await CheckForQVaultKeyAsync();

                // Live Update Drive Status every 3 seconds
                if (_overlayTicks % 3 == 0)
                {
                    UpdateLiveDriveStatus();
                }
            }
            finally
            {
                _isDetecting = false;
            }
        }

        private async void UpdateLiveDriveStatus()
        {
            if (DrivesComboBox.SelectedItem is ComboBoxItem item && item.DataContext != null)
            {
                var t = item.DataContext.GetType();
                string driveLetter = (string)(t.GetProperty("DriveLetter")?.GetValue(item.DataContext) ?? "");
                if (!string.IsNullOrEmpty(driveLetter))
                {
                    var status = await Task.Run(() => BitLockerManager.GetDriveStatus(driveLetter));
                    if (status != null)
                    {
                        uint newProtection = status.ProtectionStatus;
                        // Read current protection from DataContext
                        uint oldProtection = (uint)(t.GetProperty("ProtectionStatus")?.GetValue(item.DataContext) ?? 2u);
                        
                        if (newProtection != oldProtection)
                        {
                            string deviceId = (string)(t.GetProperty("DeviceId")?.GetValue(item.DataContext) ?? "");
                            // Create new anonymous type with updated protection
                            item.DataContext = new { ProtectionStatus = newProtection, DriveLetter = driveLetter, DeviceId = deviceId };
                            
                            // Update the UI content text
                            string statusLabel = newProtection switch
                            {
                                0 => "🔓 Not Encrypted",
                                1 => "🔒 Encrypted",
                                _ => "❓ Unknown"
                            };

                            item.Content = string.IsNullOrEmpty(driveLetter)
                                ? $"{statusLabel}  —  {deviceId}"
                                : $"{statusLabel}  —  {driveLetter}";
                            
                            // Re-trigger the selection change logic to update the UI buttons
                            DrivesComboBox_SelectionChanged(null, null);
                        }
                    }
                }
            }
        }

        private void UpdateOverlayText()
        {
            int remaining = 10 - _overlayTicks;
            if (remaining > 0)
            {
                TimeoutText.Text = $"Timeout in {remaining}s";
            }
        }

        private void HideOverlay()
        {
            if (_overlayHidden) return;
            _overlayHidden = true;

            DoubleAnimation fadeOut = new DoubleAnimation(1, 0, TimeSpan.FromSeconds(0.5));
            fadeOut.Completed += (s, ev) => { WaitingOverlay.Visibility = Visibility.Collapsed; };
            WaitingOverlay.BeginAnimation(UIElement.OpacityProperty, fadeOut);
        }

        private void RefreshBtn_Click(object sender, RoutedEventArgs e)
        {
            _ = CheckForQVaultKeyAsync();
        }

        private void ChkSimulate_Changed(object sender, RoutedEventArgs e)
        {
            _ = CheckForQVaultKeyAsync();
        }

        private async Task CheckForQVaultKeyAsync()
        {
            string port = null;

            if (ChkSimulate.IsChecked == true)
            {
                port = "COM_SIMULATED";
            }
            else
            {
                port = await Task.Run(() => GetQVaultComPort());
            }

            if (!string.IsNullOrEmpty(port))
            {
                if (_detectedComPort != port)
                {
                    _detectedComPort = port;
                    UpdateStatusUI(true, port);
                    HideOverlay();
                }
            }
            else
            {
                if (_detectedComPort != null)
                {
                    _detectedComPort = null;
                    UpdateStatusUI(false, null);
                }
                else if (_overlayHidden && !SetupContainer.IsEnabled) // Initial State if timeout reached without insert
                {
                    UpdateStatusUI(false, null);
                }
            }
        }

        private void UpdateStatusUI(bool isConnected, string port)
        {
            if (isConnected)
            {
                _pulseStoryboard.Stop(StatusDot);
                StatusDot.Opacity = 1.0;

                KeyStatusText.Text = $"Active on {port}";
                KeyStatusText.Foreground = new SolidColorBrush(Color.FromRgb(0, 255, 204)); // #00FFCC
                StatusDot.Fill = new SolidColorBrush(Color.FromRgb(0, 255, 204));
                if (StatusDot.Effect is DropShadowEffect shadow) shadow.Color = Color.FromRgb(0, 255, 204);
                
                // Enable Setup panel
                if (!SetupContainer.IsEnabled)
                {
                    SetupContainer.IsEnabled = true;
                    DoubleAnimation fadeIn = new DoubleAnimation(0.3, 1.0, TimeSpan.FromSeconds(0.4));
                    SetupContainer.BeginAnimation(UIElement.OpacityProperty, fadeIn);
                }
            }
            else
            {
                KeyStatusText.Text = "Disconnected";
                KeyStatusText.Foreground = new SolidColorBrush(Color.FromRgb(255, 51, 51)); // #FF3333
                StatusDot.Fill = new SolidColorBrush(Color.FromRgb(255, 51, 51));
                if (StatusDot.Effect is DropShadowEffect shadow) shadow.Color = Color.FromRgb(255, 51, 51);
                
                _pulseStoryboard.Begin(StatusDot);

                // Disable Setup panel
                if (SetupContainer.IsEnabled)
                {
                    SetupContainer.IsEnabled = false;
                    DoubleAnimation fadeOut = new DoubleAnimation(1.0, 0.3, TimeSpan.FromSeconds(0.4));
                    SetupContainer.BeginAnimation(UIElement.OpacityProperty, fadeOut);
                }
            }
        }

        private void LoadBitLockerDrives()
        {
            DrivesComboBox.Items.Clear();
            try
            {
                using var searcher = new ManagementObjectSearcher(
                    @"root\CIMV2\Security\MicrosoftVolumeEncryption",
                    "SELECT * FROM Win32_EncryptableVolume");

                foreach (ManagementObject vol in searcher.Get())
                {
                    string deviceId    = vol["DeviceID"]?.ToString()    ?? "";
                    string driveLetter = vol["DriveLetter"]?.ToString() ?? "";
                    if (string.IsNullOrEmpty(deviceId)) continue;

                    // Query protection status inline
                    var statusResult = vol.InvokeMethod("GetProtectionStatus", null, null);
                    uint protection  = statusResult != null ? (uint)statusResult["ProtectionStatus"] : 2;

                    string statusLabel = protection switch
                    {
                        0 => "🔓 Not Encrypted",
                        1 => "🔒 Encrypted",
                        _ => "❓ Unknown"
                    };

                    string displayName = string.IsNullOrEmpty(driveLetter)
                        ? $"{statusLabel}  —  {deviceId}"
                        : $"{statusLabel}  —  {driveLetter}";

                    var item = new ComboBoxItem
                    {
                        Content = displayName,
                        Tag     = deviceId,
                        // Store protection status + drive letter for use in SelectionChanged
                        DataContext = new { ProtectionStatus = protection, DriveLetter = driveLetter, DeviceId = deviceId }
                    };
                    DrivesComboBox.Items.Add(item);
                }

                if (DrivesComboBox.Items.Count > 0)
                    DrivesComboBox.SelectedIndex = 0;
                else
                    DrivesComboBox.Items.Add(new ComboBoxItem
                    { Content = "No encryptable drives found.", IsEnabled = false });
            }
            catch (ManagementException mex) when (mex.ErrorCode == ManagementStatus.AccessDenied)
            {
                DrivesComboBox.Items.Add(new ComboBoxItem
                { Content = "Access Denied — run as Administrator", IsEnabled = false });
            }
            catch (Exception ex)
            {
                DrivesComboBox.Items.Add(new ComboBoxItem
                { Content = $"Error: {ex.Message}", IsEnabled = false });
            }
        }

        private void DrivesComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (DrivesComboBox.SelectedItem is not ComboBoxItem item) return;
            if (item.DataContext == null) return;

            var t = item.DataContext.GetType();
            uint   protection  = (uint)(t.GetProperty("ProtectionStatus")?.GetValue(item.DataContext) ?? 2u);
            string driveLetter = (string)(t.GetProperty("DriveLetter")?.GetValue(item.DataContext) ?? "");

            DriveStatusBadge.Visibility = Visibility.Visible;
            DriveInfoText.Visibility    = Visibility.Visible;

            if (protection == 1) // Already encrypted
            {
                DriveStatusBadge.Background = new SolidColorBrush(Color.FromRgb(0, 40, 20));
                DriveStatusBadge.BorderBrush = new SolidColorBrush(Color.FromRgb(0, 180, 80));
                DriveStatusBadge.BorderThickness = new Thickness(1);
                DriveStatusBadgeText.Text       = "Already Encrypted";
                DriveStatusBadgeText.Foreground  = new SolidColorBrush(Color.FromRgb(0, 220, 100));
                DriveInfoText.Text = $"✓ This drive is encrypted. The same password will be sent to the hardware key.";
                DriveInfoText.Foreground = new SolidColorBrush(Color.FromRgb(0, 180, 80));
                SetupButton.Content = "PROVISION HARDWARE KEY";
            }
            else // Not yet encrypted
            {
                DriveStatusBadge.Background = new SolidColorBrush(Color.FromRgb(40, 20, 0));
                DriveStatusBadge.BorderBrush = new SolidColorBrush(Color.FromRgb(200, 100, 0));
                DriveStatusBadge.BorderThickness = new Thickness(1);
                DriveStatusBadgeText.Text       = "Not Encrypted";
                DriveStatusBadgeText.Foreground  = new SolidColorBrush(Color.FromRgb(255, 150, 30));
                DriveInfoText.Text = $"⚠ This drive will be encrypted with BitLocker FIRST, then provisioned to the key.";
                DriveInfoText.Foreground = new SolidColorBrush(Color.FromRgb(200, 140, 30));
                SetupButton.Content = "ENCRYPT & PROVISION";
            }
        }

        private string GetQVaultComPort()
        {
            try
            {
                using (var searcher = new ManagementObjectSearcher("SELECT * FROM Win32_PnPEntity WHERE Caption LIKE '%(COM%'"))
                {
                    foreach (var device in searcher.Get())
                    {
                        string hardwareId = device["PNPDeviceID"]?.ToString() ?? "";
                        if (hardwareId.Contains(TargetHWID))
                        {
                            string caption = device["Caption"].ToString();
                            Match match = Regex.Match(caption, @"\((COM\d+)\)");
                            if (match.Success)
                            {
                                return match.Groups[1].Value; 
                            }
                        }
                    }
                }
            }
            catch
            {
                // Ignore silent WMI failures during timer ticks
            }
            return null;
        }

        private void PasswordMode_Changed(object sender, RoutedEventArgs e)
        {
            if (RbManual == null || RbAuto == null || RbRecover == null) return;

            if (RbManual.IsChecked == true)
            {
                ManualPasswordBorder.Visibility = Visibility.Visible;
                AutoPasswordBorder.Visibility = Visibility.Collapsed;
                SeedRecoverBorder.Visibility = Visibility.Collapsed;
            }
            else if (RbAuto.IsChecked == true)
            {
                ManualPasswordBorder.Visibility = Visibility.Collapsed;
                AutoPasswordBorder.Visibility = Visibility.Visible;
                SeedRecoverBorder.Visibility = Visibility.Collapsed;
            }
            else if (RbRecover.IsChecked == true)
            {
                ManualPasswordBorder.Visibility = Visibility.Collapsed;
                AutoPasswordBorder.Visibility = Visibility.Collapsed;
                SeedRecoverBorder.Visibility = Visibility.Visible;
            }
        }

        private string GenerateSecurePassword(int length)
        {
            const string validChars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@#$%^&*()-_=+";
            StringBuilder res = new StringBuilder();
            
            byte[] uintBuffer = new byte[sizeof(uint)];

            while (length-- > 0)
            {
                RandomNumberGenerator.Fill(uintBuffer);
                uint num = BitConverter.ToUInt32(uintBuffer, 0);
                res.Append(validChars[(int)(num % (uint)validChars.Length)]);
            }
            
            return res.ToString();
        }

        private string DerivePasswordFromSeed(string mnemonicStr)
        {
            try
            {
                var mnemonic = new Mnemonic(mnemonicStr, Wordlist.English);
                // Deterministic derivation: Hash the 512-bit seed
                byte[] seed = mnemonic.DeriveSeed("");
                using var sha256 = SHA256.Create();
                byte[] hash = sha256.ComputeHash(seed);
                // Convert to a robust 32-char password by encoding in Base64 and taking 32 chars
                // E.g. we want it to be valid ASCII chars without spaces. Base64 is perfect.
                string base64 = Convert.ToBase64String(hash);
                return base64.Substring(0, 32);
            }
            catch (Exception)
            {
                return ""; // Invalid seed
            }
        }

        private async void SetupButton_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(_detectedComPort))
            {
                MessageBox.Show("Q-Vault hardware key is not connected.", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                return;
            }

            if (DrivesComboBox.SelectedItem is not ComboBoxItem selectedDrive
                || selectedDrive.Tag == null || !selectedDrive.IsEnabled)
            {
                MessageBox.Show("Please select a valid target drive.", "Warning", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            string targetGuid   = selectedDrive.Tag.ToString()!;
            uint   protection   = 1u;
            uint   conversion   = 0u;
            string driveLetter  = "";
            if (selectedDrive.DataContext is object dc)
            {
                var t = dc.GetType();
                driveLetter = (string)(t.GetProperty("DriveLetter")?.GetValue(dc)   ?? "");
            }
            string finalPassword = "";

            // Stop timer early to prevent WMI deadlocks on the UI thread
            _detectionTimer.Stop();

            try
            {
                // Check Live Protection Status right now
            if (!string.IsNullOrEmpty(driveLetter))
            {
                var liveStatus = await Task.Run(() => BitLockerManager.GetDriveStatus(driveLetter));
                if (liveStatus != null) 
                {
                    protection = liveStatus.ProtectionStatus;
                    conversion = liveStatus.ConversionStatus;
                }
            }

            // ── Password resolution ────────────────────────────────────────
            if (RbManual.IsChecked == true)
            {
                finalPassword = VaultPasswordBox.Password;
                if (string.IsNullOrEmpty(finalPassword))
                {
                    MessageBox.Show("Please enter the Vault password.", "Warning", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }
            }
            else if (RbRecover.IsChecked == true)
            {
                string inputSeed = SeedInputBox.Text.Trim();
                string[] words = inputSeed.Split(new[] { ' ', '\r', '\n', '\t' }, StringSplitOptions.RemoveEmptyEntries);
                if (words.Length != 12)
                {
                    MessageBox.Show("Please enter exactly 12 words for your seed.", "Warning", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }

                inputSeed = string.Join(" ", words);
                finalPassword = DerivePasswordFromSeed(inputSeed);
                if (string.IsNullOrEmpty(finalPassword))
                {
                    MessageBox.Show("Invalid BIP39 Seed. Please check the words.", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }
            }
            else // Auto-Generate Seed
            {
                // Generate a 12-word BIP39 mnemonic
                var mnemonic = new Mnemonic(Wordlist.English, WordCount.Twelve);
                string generatedSeed = mnemonic.ToString();
                
                finalPassword = DerivePasswordFromSeed(generatedSeed);

                var sfd = new SaveFileDialog
                {
                    Title    = "Save Q-Vault Recovery Seed",
                    Filter   = "Text Files (*.txt)|*.txt",
                    FileName = "QVault_RecoverySeed.txt"
                };
                if (sfd.ShowDialog() == true)
                {
                    try
                    {
                        File.WriteAllText(sfd.FileName,
                            $"Q-VAULT RECOVERY SEED\nDrive GUID: {targetGuid}\n\n12-WORD SEED:\n{generatedSeed}\n\nWARNING: KEEP THIS FILE SECURE. ANYONE WITH THESE 12 WORDS CAN UNLOCK YOUR DRIVE AND RE-PROVISION THE HARDWARE KEY.");
                    }
                    catch (Exception ex)
                    {
                        MessageBox.Show($"Failed to save recovery file: {ex.Message}\nSetup aborted.",
                                        "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                        return;
                    }
                }
                else
                {
                    MessageBox.Show("Recovery file must be saved. Setup aborted.",
                                    "Aborted", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }
            }

            SetupButton.IsEnabled  = false;
            SetupButton.Content    = "WORKING...";

            // ── PRE-PHASE: Unlock if drive is locked ────────────────────
            if (protection == 2 && !string.IsNullOrEmpty(driveLetter))
            {
                SetupButton.Content = "UNLOCKING DRIVE...";
                var unlockRes = await Task.Run(() => BitLockerManager.UnlockDriveWithPassword(driveLetter, finalPassword));
                if (!unlockRes.Success)
                {
                    MessageBox.Show($"Failed to unlock drive:\n{unlockRes.Message}\nCheck your seed or password.", "Unlock Failed", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }
                
                // Refresh status
                var st = await Task.Run(() => BitLockerManager.GetDriveStatus(driveLetter));
                if (st != null)
                {
                    protection = st.ProtectionStatus;
                    conversion = st.ConversionStatus;
                }
            }

            // ── PHASE 1: Encrypt the drive if it isn't already ──────────
                if (protection != 1 && conversion != 1 && conversion != 2 && !string.IsNullOrEmpty(driveLetter))
                {
                    SetupButton.Content = "ENCRYPTING DRIVE...";
                    EncryptProgressPanel.Visibility = Visibility.Visible;
                    EncryptStatusText.Text  = "Starting BitLocker...";
                    EncryptProgressBar.Value = 0;
                    EncryptPercentText.Text  = "0%";

                    BitLockerResult encResult = await Task.Run(() =>
                        BitLockerManager.EncryptDriveWithPassword(driveLetter, finalPassword));

                    if (!encResult.Success)
                    {
                        MessageBox.Show($"Encryption failed:\n{encResult.Message}",
                                        "Encryption Error", MessageBoxButton.OK, MessageBoxImage.Error);
                        return;
                    }

                    // Poll encryption progress until 100 %
                    EncryptStatusText.Text = "Encrypting...";
                    while (true)
                    {
                        await Task.Delay(2500);
                        int pct = await Task.Run(() => BitLockerManager.GetEncryptionProgress(driveLetter));
                        if (pct >= 0)
                        {
                            EncryptProgressBar.Value = pct;
                            EncryptPercentText.Text  = $"{pct}%";
                        }

                        var st = await Task.Run(() => BitLockerManager.GetDriveStatus(driveLetter));
                        if (st != null) EncryptStatusText.Text = st.ConversionStatusText;

                        // Done when fully encrypted (ConversionStatus == 1)
                        if (st?.ConversionStatus == 1 || pct >= 100) break;
                    }

                    EncryptStatusText.Text   = "Encrypted ✓";
                    EncryptProgressBar.Value = 100;
                    EncryptPercentText.Text  = "100%";
                }

                // ── PHASE 2: Send to ESP ────────────────────────────────────
                ProvisionProgressPanel.Visibility = Visibility.Visible;
                ProvisionStatusText.Text = "Stopping background service...";
                SetupButton.Content = "PROVISIONING KEY...";

                if (_detectedComPort == "COM_SIMULATED")
                {
                    ProvisionStatusText.Text = "Simulating...";
                    await Task.Delay(1500);
                    MessageBox.Show($"[SIMULATED] Would send: SETUP|{targetGuid}|{finalPassword}",
                                    "Provisioned (Simulated)", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                else
                {
                    string comPort     = _detectedComPort!;
                    string cmdPassword = finalPassword;
                    string cmdGuid     = targetGuid;

                    // Stop service so it releases the COM port
                    ProvisionStatusText.Text = "Stopping QVault service...";
                    SetupButton.Content = "STOPPING SERVICE...";
                    await StopQVaultService();
                    await Task.Delay(600); // extra safety gap

                    ProvisionStatusText.Text = "Waiting for ESP32 setup beacon...";
                    SetupButton.Content = "WAITING FOR ESP...";
                    bool success = false;
                    string provisionError = "";

                    try
                    {
                        (success, provisionError) = await Task.Run(() =>
                        {
                            using SerialPort port = new SerialPort(comPort, 115200)
                            {
                                ReadTimeout  = 5000,
                                WriteTimeout = 2000,
                                NewLine      = "\n",
                                DtrEnable    = false,
                                RtsEnable    = false
                            };

                            try { port.Open(); }
                            catch (UnauthorizedAccessException)
                            {
                                return (false, "Access Denied: The COM port is still locked.\nMake sure the QVault service is fully stopped and try again.");
                            }
                            catch (Exception ex)
                            {
                                return (false, $"Failed to open {comPort}: {ex.Message}");
                            }

                            // Wait up to 10 seconds for AWAITING_SETUP beacon
                            DateTime t0 = DateTime.Now;
                            bool beaconFound = false;
                            while ((DateTime.Now - t0).TotalSeconds < 10)
                            {
                                try
                                {
                                    string line = port.ReadLine().Trim();
                                    if (line.Contains("AWAITING_SETUP"))
                                    { beaconFound = true; break; }
                                }
                                catch (TimeoutException) { }
                            }

                            if (!beaconFound)
                            {
                                port.Close();
                                return (false, "Hardware key is not in Setup Mode.\n\nMake sure you held BOOT for 5+ seconds to trigger factory reset, then try again.");
                            }

                            // Send SETUP command
                            port.WriteLine($"SETUP|{cmdGuid}|{cmdPassword}");

                            // Wait up to 5 seconds for SETUP_SUCCESS acknowledgement
                            t0 = DateTime.Now;
                            while ((DateTime.Now - t0).TotalSeconds < 5)
                            {
                                try
                                {
                                    string ack = port.ReadLine().Trim();
                                    if (ack.Contains("SETUP_SUCCESS"))
                                    { port.Close(); return (true, ""); }
                                }
                                catch (TimeoutException) { }
                            }

                            port.Close();
                            return (false, "Device did not acknowledge the setup command within 5 seconds.");
                        });
                    }
                    finally
                    {
                        ProvisionStatusText.Text = "Restarting service...";
                        await StartQVaultService();
                        ProvisionProgressPanel.Visibility = Visibility.Collapsed;
                    }

                    if (success)
                    {
                        ProvisionProgressPanel.Visibility = Visibility.Collapsed;
                        MessageBox.Show(
                            "✅ Vault Provisioned Successfully!\n\nThe background service has been restarted and is now managing your vault.",
                            "Provisioned", MessageBoxButton.OK, MessageBoxImage.Information);
                    }
                    else if (!string.IsNullOrEmpty(provisionError))
                        MessageBox.Show(provisionError, "Provisioning Failed", MessageBoxButton.OK, MessageBoxImage.Error);
                }

                // Zero-Knowledge wipe
                VaultPasswordBox.Password = string.Empty;
                SeedInputBox.Text = string.Empty;
                finalPassword = string.Empty;
                RbManual.IsChecked = true;
                EncryptProgressPanel.Visibility = Visibility.Collapsed;
                ProvisionProgressPanel.Visibility = Visibility.Collapsed;
                LoadBitLockerDrives(); // Refresh drive list

                // Restart detection timer
                _detectionTimer.Start();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Unexpected Error: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                SetupButton.IsEnabled = true;
                SetupButton.Content   = protection == 1 ? "PROVISION HARDWARE KEY" : "ENCRYPT & PROVISION";
                ProvisionProgressPanel.Visibility = Visibility.Collapsed;
                // Always restart the detection timer
                _detectionTimer.Start();
            }
        }

        private async Task StopQVaultService()
        {
            await Task.Run(() =>
            {
                try
                {
                    var psi = new System.Diagnostics.ProcessStartInfo("sc", "stop QVault")
                    {
                        CreateNoWindow  = true,
                        UseShellExecute = false
                    };
                    System.Diagnostics.Process.Start(psi)?.WaitForExit(3000);
                }
                catch { }
            });
            // Async delay to let OS release the COM port handle
            await Task.Delay(1500);
        }

        private async Task StartQVaultService()
        {
            await Task.Run(() =>
            {
                try
                {
                    System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo("sc", "start QVault") { CreateNoWindow = true, UseShellExecute = false })?.WaitForExit(2000);
                }
                catch { }
            });
        }
    }
}
