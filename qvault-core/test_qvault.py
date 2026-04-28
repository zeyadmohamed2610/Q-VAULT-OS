import os
import shutil
import time
import sys

# Windows default console might not support utf-8 print without it
sys.stdout.reconfigure(encoding='utf-8')

try:
    import qvault_core
    print("[OK] Module imported successfully: qvault_core")
except Exception as e:
    print(f"[FAIL] Failed to import qvault_core: {e}")
    exit(1)

test_dir = "test_data"
if os.path.exists(test_dir):
    shutil.rmtree(test_dir)
os.makedirs(test_dir, exist_ok=True)

print("\n--- Validating API ---")
try:
    engine = qvault_core.SecurityEngine(test_dir)
    print("[OK] Engine initialized")

    # Step 1: Login as default admin
    admin_token = engine.login("admin", "admin123")
    print(f"[OK] Admin logged in. Token: {admin_token}")

    # Step 2: Create a new user
    engine.create_user(admin_token, "testuser", "testpass", "user")
    print("[OK] Created testuser")

    # Step 3: Login as testuser
    user_token = engine.login("testuser", "testpass")
    print(f"[OK] Testuser logged in. Token: {user_token}")

    # Step 4: Store a secret
    engine.store_secret(user_token, "my_secret", "super_secret_value")
    print("[OK] Secret stored successfully")

    # Step 5: Retrieve the secret
    retrieved = engine.get_secret(user_token, "my_secret")
    print(f"[OK] Secret retrieved: {retrieved}")
    assert retrieved == "super_secret_value", "Secret mismatch!"

    # List secrets
    secrets = engine.list_secrets(user_token)
    print(f"[OK] Secrets list: {secrets}")
    assert "my_secret" in secrets, "Secret not in list!"

    print("\n--- Validating Error Handling ---")
    # Wrong password
    try:
        engine.login("testuser", "wrongpass")
        print("[FAIL] Login with wrong password should have failed")
        exit(1)
    except Exception as e:
        print(f"[OK] Caught expected login error: {e}")

    # Invalid token
    try:
        engine.get_secret("invalid-token", "my_secret")
        print("[FAIL] get_secret with invalid token should have failed")
        exit(1)
    except Exception as e:
        print(f"[OK] Caught expected invalid token error: {e}")

    # Input too large (testing FFI limits)
    try:
        engine.store_secret(user_token, "A"*500, "val")
        print("[FAIL] store_secret with too large key should have failed")
        exit(1)
    except Exception as e:
        print(f"[OK] Caught expected input too large error: {e}")

    # Step 8: Stress Test
    print("\n--- Stress Testing ---")
    for i in range(100):
        engine.store_secret(user_token, f"stress_key_{i}", f"val_{i}")

    val = engine.get_secret(user_token, "stress_key_50")
    print(f"[OK] Stress retrieval successful: {val}")

    # Check logout
    engine.logout(user_token)
    try:
        engine.list_secrets(user_token)
        print("[FAIL] list_secrets with logged out token should have failed")
        exit(1)
    except Exception as e:
        print(f"[OK] Caught expected error after logout: {e}")

    print("\n[OK] ALL TESTS PASSED END-TO-END")

except Exception as e:
    print(f"[FAIL] Test failed unexpectedly: {e}")
    exit(1)
