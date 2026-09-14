/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    images: {
        remotePatterns: [
            {
                protocol: 'http',
                hostname: '192.168.38.209',
            }
        ]
    },
    serverExternalPackages: ['snowflake-sdk'],
}

module.exports = nextConfig
