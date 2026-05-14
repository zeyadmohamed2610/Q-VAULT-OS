//! Build script for Q-Vault Core
//! 
//! This build script ensures proper configuration for the PyO3 extension

fn main() {
    // Tell Cargo to rerun this script if something changes
    println!("cargo:rerun-if-changed=src/");
    
    // PyO3 configuration is handled in Cargo.toml
    // This script is for any additional build steps if needed
}