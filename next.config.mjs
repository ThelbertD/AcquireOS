/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // The Python functions in /api are deployed by Vercel as separate serverless functions and
  // are not part of the Next.js build. In development they are not running at all, so `npm run
  // dev` proxies /api/* to a local Python server started by `npm run api` (see README).
  async rewrites() {
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/:path*',
          destination: 'http://127.0.0.1:8787/api/:path*',
        },
      ]
    }
    return []
  },
}

export default nextConfig
