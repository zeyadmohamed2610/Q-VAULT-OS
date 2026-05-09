import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Transpile Three.js ecosystem packages
  transpilePackages: [
    "three",
    "@react-three/fiber",
    "@react-three/drei",
    "@react-three/postprocessing",
    "postprocessing",
  ],

  // Turbopack config (Next.js 16 default bundler)
  turbopack: {
    rules: {
      "*.glsl": { loaders: ["raw-loader"], as: "*.js" },
      "*.vert": { loaders: ["raw-loader"], as: "*.js" },
      "*.frag": { loaders: ["raw-loader"], as: "*.js" },
    },
  },

  // Webpack config (used for production builds / non-turbopack)
  webpack(config) {
    // Exclude the raw model/ source directory from webpack processing
    config.watchOptions = {
      ...config.watchOptions,
      ignored: [
        ...(Array.isArray(config.watchOptions?.ignored)
          ? config.watchOptions.ignored
          : config.watchOptions?.ignored
          ? [config.watchOptions.ignored]
          : []),
        path.resolve(__dirname, "model"),
        "**/*.glb",
      ],
    };
    return config;
  },
};

export default nextConfig;
