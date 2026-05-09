/** @type {import('next').NextConfig} */
const nextConfig = {
  ...(process.env.NEXT_OUTPUT_MODE === "export" ? { output: "export" } : {}),
};

export default nextConfig;

