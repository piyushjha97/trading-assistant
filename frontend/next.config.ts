import type { NextConfig } from "next";

const config: NextConfig = {
  agentRules: false,
  devIndicators: false,
  poweredByHeader: false,
  logging: { incomingRequests: { ignore: [/^\/api\/kite\/callback(?:[/?]|$)/] } },
};

export default config;
