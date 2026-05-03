using System;
using System.Management;

namespace PQC_Vault
{
    /// <summary>
    /// Result object returned by BitLocker operations.
    /// Contains success status, a human-readable message, and an optional WMI return code.
    /// </summary>
    public class BitLockerResult
    {
        public bool Success { get; init; }
        public string Message { get; init; } = string.Empty;
        public uint? WmiReturnCode { get; init; }

        public static BitLockerResult Ok(string message = "Success") =>
            new() { Success = true, Message = message };

        public static BitLockerResult Fail(string message, uint? code = null) =>
            new() { Success = false, Message = message, WmiReturnCode = code };
    }

    /// <summary>
    /// Represents the current encryption state of a drive volume.
    /// </summary>
    public class DriveEncryptionStatus
    {
        /// <summary>Percentage complete (0–100). -1 if unavailable.</summary>
        public int ProgressPercent { get; init; } = -1;

        /// <summary>
        /// Protection status from WMI GetProtectionStatus:
        ///   0 = Unprotected, 1 = Protected, 2 = Unknown
        /// </summary>
        public uint ProtectionStatus { get; init; }

        /// <summary>
        /// Conversion status from WMI GetConversionStatus:
        ///   0 = FullyDecrypted, 1 = FullyEncrypted, 2 = EncryptionInProgress,
        ///   3 = DecryptionInProgress, 4 = EncryptionPaused, 5 = DecryptionPaused
        /// </summary>
        public uint ConversionStatus { get; init; }

        public string ProtectionStatusText => ProtectionStatus switch
        {
            0 => "Unprotected",
            1 => "Protected",
            _ => "Unknown"
        };

        public string ConversionStatusText => ConversionStatus switch
        {
            0 => "Fully Decrypted",
            1 => "Fully Encrypted",
            2 => "Encryption In Progress",
            3 => "Decryption In Progress",
            4 => "Encryption Paused",
            5 => "Decryption Paused",
            _ => "Unknown"
        };
    }

    /// <summary>
    /// Static helper class for all BitLocker WMI operations.
    /// IMPORTANT: All methods require the application to be running as Administrator.
    /// WMI Namespace: root\CIMv2\Security\MicrosoftVolumeEncryption
    /// WMI Class:     Win32_EncryptableVolume
    /// </summary>
    public static class BitLockerManager
    {
        private const string WmiNamespace = @"root\CIMv2\Security\MicrosoftVolumeEncryption";
        private const string WmiClass = "Win32_EncryptableVolume";

        // ──────────────────────────────────────────────────────────────────────
        // PRIVATE HELPER
        // ──────────────────────────────────────────────────────────────────────

        /// <summary>
        /// Retrieves the WMI ManagementObject for a specific drive letter.
        /// Returns null if not found.
        /// </summary>
        private static ManagementObject? GetVolumeObject(string driveLetter)
        {
            // Normalise: ensure format is "C:" not "C" or "C:\"
            string normalized = driveLetter.TrimEnd('\\').TrimEnd(':') + ":";

            var scope = new ManagementScope(WmiNamespace);
            scope.Connect();

            var query = new ObjectQuery(
                $"SELECT * FROM {WmiClass} WHERE DriveLetter = '{normalized}'");

            using var searcher = new ManagementObjectSearcher(scope, query);
            foreach (ManagementObject vol in searcher.Get())
            {
                // Return the first (and only) match — caller owns the object
                return vol;
            }

            return null;
        }

        // ──────────────────────────────────────────────────────────────────────
        // PUBLIC METHOD 1 — EncryptDriveWithPassword
        // ──────────────────────────────────────────────────────────────────────

        /// <summary>
        /// Encrypts an unencrypted drive using a user-supplied passphrase.
        ///
        /// Workflow:
        ///   Step A: ProtectKeyWithPassphrase  — registers the password as a key protector.
        ///   Step B: Encrypt                   — starts the background encryption process.
        ///
        /// Requires: Administrator privileges.
        /// </summary>
        /// <param name="driveLetter">Drive letter, e.g. "D" or "D:" or "D:\"</param>
        /// <param name="password">
        ///   The passphrase to protect the volume.
        ///   Minimum 8 characters required by BitLocker policy.
        /// </param>
        /// <returns>A <see cref="BitLockerResult"/> indicating success or failure.</returns>
        public static BitLockerResult EncryptDriveWithPassword(string driveLetter, string password)
        {
            if (string.IsNullOrWhiteSpace(driveLetter))
                return BitLockerResult.Fail("Drive letter cannot be empty.");

            if (string.IsNullOrWhiteSpace(password) || password.Length < 8)
                return BitLockerResult.Fail("Password must be at least 8 characters.");

            try
            {
                using ManagementObject? volume = GetVolumeObject(driveLetter);
                if (volume is null)
                    return BitLockerResult.Fail($"Drive '{driveLetter}' was not found in the WMI namespace. " +
                                                "Make sure the drive is visible to Windows.");

                // ── STEP A: Add a Passphrase Key Protector ──────────────────────────
                //
                // WMI method: ProtectKeyWithPassphrase
                // Parameters:
                //   FriendlyName  (string)     — optional label for the protector (we pass empty)
                //   Passphrase    (string)      — the user-supplied password
                // Out parameter:
                //   VolumeKeyProtectorID (string) — unique ID assigned to this protector (not used here)
                //
                // Common return codes:
                //   0       = Success
                //   0x8031006D (2150072429) = The passphrase does not meet Windows policy requirements

                using ManagementBaseObject protectorInParams =
                    volume.GetMethodParameters("ProtectKeyWithPassphrase");

                protectorInParams["FriendlyName"] = string.Empty; // Optional display name
                protectorInParams["Passphrase"]   = password;      // The actual passphrase

                using ManagementBaseObject protectorResult =
                    volume.InvokeMethod("ProtectKeyWithPassphrase", protectorInParams, null);

                uint protectorCode = (uint)protectorResult["ReturnValue"];
                if (protectorCode != 0 && protectorCode != 0x80310000)
                    return BitLockerResult.Fail(
                        $"Failed to add passphrase protector. WMI Code: 0x{protectorCode:X8}\n" +
                        "Common causes: Password policy restrictions, drive already protected.",
                        protectorCode);

                // ── STEP B: Start Encryption ────────────────────────────────────────
                //
                // WMI method: Encrypt
                // Parameters:
                //   EncryptionMethod (uint32) — cipher to use:
                //     0  = Unspecified  (Windows picks the default, usually AES-128-CBC on older OS)
                //     3  = AES-128-CBC
                //     4  = AES-256-CBC
                //     6  = AES-128-XTS  (Windows 10 1511+ only, for OS drives)
                //     7  = AES-256-XTS  (Windows 10 1511+ only — strongest option, recommended)
                //   EncryptionFlags (uint32) — bitfield options:
                //     0x00 = Default (encrypt used space only is NOT set — encrypts full disk)
                //     0x01 = Encrypt used space only (faster for new drives)
                //
                // We request AES-256-XTS with used-space-only for speed.
                // If the OS doesn't support method 7, WMI will return an error and we fall back.

                using ManagementBaseObject encryptInParams =
                    volume.GetMethodParameters("Encrypt");

                encryptInParams["EncryptionMethod"] = (uint)7;   // AES-256-XTS (strongest)
                encryptInParams["EncryptionFlags"]  = (uint)0x01; // Encrypt used space only (faster)

                using ManagementBaseObject encryptResult =
                    volume.InvokeMethod("Encrypt", encryptInParams, null);

                uint encryptCode = (uint)encryptResult["ReturnValue"];

                if (encryptCode == 0)
                    return BitLockerResult.Ok(
                        "Encryption started successfully using AES-256-XTS. " +
                        "The drive will encrypt in the background.");

                // Code 0x80310000 means encryption is already in progress — treat as soft success
                if (encryptCode == 0x80310000)
                    return BitLockerResult.Ok("Encryption is already in progress on this drive.");

                // If AES-256-XTS failed (unsupported on this OS), retry with AES-256-CBC
                encryptInParams["EncryptionMethod"] = (uint)4; // AES-256-CBC fallback

                using ManagementBaseObject fallbackResult =
                    volume.InvokeMethod("Encrypt", encryptInParams, null);

                uint fallbackCode = (uint)fallbackResult["ReturnValue"];

                if (fallbackCode == 0)
                    return BitLockerResult.Ok(
                        "Encryption started using AES-256-CBC (XTS not supported on this system).");

                return BitLockerResult.Fail(
                    $"Failed to start encryption. WMI Code: 0x{fallbackCode:X8}",
                    fallbackCode);
            }
            catch (ManagementException mex) when (mex.ErrorCode == ManagementStatus.AccessDenied)
            {
                return BitLockerResult.Fail(
                    "Access Denied. Please run the application as Administrator to manage BitLocker.");
            }
            catch (Exception ex)
            {
                return BitLockerResult.Fail($"Unexpected error during encryption: {ex.Message}");
            }
        }

        // ──────────────────────────────────────────────────────────────────────
        // PUBLIC METHOD 2 — UnlockDriveWithPassword
        // ──────────────────────────────────────────────────────────────────────

        public static BitLockerResult UnlockDriveWithPassword(string driveLetter, string password)
        {
            try
            {
                using ManagementObject? volume = GetVolumeObject(driveLetter);
                if (volume is null) return BitLockerResult.Fail("Drive not found.");

                using ManagementBaseObject inParams = volume.GetMethodParameters("UnlockWithPassphrase");
                inParams["Passphrase"] = password;

                using ManagementBaseObject outParams = volume.InvokeMethod("UnlockWithPassphrase", inParams, null);
                uint retCode = (uint)outParams["ReturnValue"];

                if (retCode == 0) return BitLockerResult.Ok("Drive unlocked successfully.");
                return BitLockerResult.Fail($"Failed to unlock drive. WMI Code: 0x{retCode:X8}", retCode);
            }
            catch (Exception ex)
            {
                return BitLockerResult.Fail($"Unlock error: {ex.Message}");
            }
        }

        // ──────────────────────────────────────────────────────────────────────
        // PUBLIC METHOD 3 — GetEncryptionProgress
        // ──────────────────────────────────────────────────────────────────────

        /// <summary>
        /// Polls the current encryption (or decryption) percentage for a drive.
        /// Intended to be called periodically from a UI DispatcherTimer to update a ProgressBar.
        /// </summary>
        /// <param name="driveLetter">Drive letter, e.g. "D"</param>
        /// <returns>
        ///   Integer from 0 to 100 representing the completion percentage.
        ///   Returns -1 on error or if the drive is not found.
        /// </returns>
        public static int GetEncryptionProgress(string driveLetter)
        {
            try
            {
                using ManagementObject? volume = GetVolumeObject(driveLetter);
                if (volume is null) return -1;

                // WMI method: GetConversionStatus
                // Out parameters:
                //   ConversionStatus       (uint32) — current state (see DriveEncryptionStatus)
                //   EncryptionPercentage   (uint32) — 0–100 percentage
                //   EncryptionFlags        (uint32) — bitfield of active flags
                //   WipingStatus           (uint32) — wiping state
                //   WipingPercentage       (uint32) — 0–100
                //   PrecisionFactor        (uint32) — divisor for precision (usually 1)

                using ManagementBaseObject result =
                    volume.InvokeMethod("GetConversionStatus", null, null);

                uint returnCode = (uint)result["ReturnValue"];
                if (returnCode != 0) return -1;

                uint percent = (uint)result["EncryptionPercentage"];
                return (int)Math.Min(percent, 100); // Guard against any out-of-range WMI values
            }
            catch
            {
                // Return -1 silently — caller will treat -1 as "unavailable"
                return -1;
            }
        }

        // ──────────────────────────────────────────────────────────────────────
        // PUBLIC METHOD 3 — GetDriveStatus
        // ──────────────────────────────────────────────────────────────────────

        /// <summary>
        /// Returns the full encryption and protection status of a drive.
        /// Combines GetProtectionStatus and GetConversionStatus into one call.
        /// </summary>
        /// <param name="driveLetter">Drive letter, e.g. "D"</param>
        /// <returns>
        ///   A <see cref="DriveEncryptionStatus"/> object.
        ///   Returns null on error.
        /// </returns>
        public static DriveEncryptionStatus? GetDriveStatus(string driveLetter)
        {
            try
            {
                using ManagementObject? volume = GetVolumeObject(driveLetter);
                if (volume is null) return null;

                // ── Protection Status ───────────────────────────────────────────────
                //
                // WMI method: GetProtectionStatus
                // Out parameter:
                //   ProtectionStatus (uint32):
                //     0 = Protection OFF  — volume key is exposed (unprotected)
                //     1 = Protection ON   — volume key is secured by a protector
                //     2 = Unknown         — could not determine status

                using ManagementBaseObject protResult =
                    volume.InvokeMethod("GetProtectionStatus", null, null);

                uint protectionStatus = (uint)protResult["ProtectionStatus"];

                // ── Conversion Status & Progress ────────────────────────────────────

                using ManagementBaseObject convResult =
                    volume.InvokeMethod("GetConversionStatus", null, null);

                uint conversionStatus = 0;
                int progressPercent   = -1;

                if ((uint)convResult["ReturnValue"] == 0)
                {
                    conversionStatus = (uint)convResult["ConversionStatus"];
                    progressPercent  = (int)(uint)convResult["EncryptionPercentage"];
                }

                return new DriveEncryptionStatus
                {
                    ProtectionStatus = protectionStatus,
                    ConversionStatus = conversionStatus,
                    ProgressPercent  = progressPercent
                };
            }
            catch (ManagementException mex) when (mex.ErrorCode == ManagementStatus.AccessDenied)
            {
                // Log or surface this to the UI if needed
                return null;
            }
            catch
            {
                return null;
            }
        }
    }
}
