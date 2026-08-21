/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/estimate',
        destination: 'http://web:8000/api/estimate'
      },
      {
        source: '/api/calibrate',
        destination: 'http://web:8000/api/calibrate'
      },
      {
        source: '/api/:path*',
        destination: `${process.env.BACKEND_URL || 'http://backend:8000'}/api/:path*`
      }
    ]
  },
  // Confine the Turbopack workspace root to this directory: a stray
  // package-lock.json above the project would otherwise be picked as root.
  // (Relative to this file, so it also works inside the Docker container.)
  turbopack: {
    root: import.meta.dirname
  }
};

export default nextConfig;
