import type { NextAuthOptions } from "next-auth";
import AzureADProvider from "next-auth/providers/azure-ad";
import CredentialsProvider from "next-auth/providers/credentials";
import { prisma } from "@/lib/prisma";

const azureConfigured = Boolean(
  process.env.AZURE_CLIENT_ID &&
  process.env.AZURE_CLIENT_SECRET &&
  process.env.AZURE_TENANT_ID
);

const demoLoginEnabled =
  process.env.ENABLE_DEMO_LOGIN === "true" || process.env.NODE_ENV !== "production";

const providers = [];

if (azureConfigured) {
  providers.push(
    AzureADProvider({
      clientId: process.env.AZURE_CLIENT_ID!,
      clientSecret: process.env.AZURE_CLIENT_SECRET!,
      tenantId: process.env.AZURE_TENANT_ID!,
      authorization: {
        params: {
          scope: "openid profile email offline_access",
        },
      },
    })
  );
}

if (demoLoginEnabled) {
  providers.push(
    CredentialsProvider({
      name: "Demo Login",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        const email = credentials?.email?.trim().toLowerCase();
        const password = credentials?.password;

        if (!email || !password) {
          return null;
        }

        const user = await prisma.user.findUnique({
          where: { email },
        });

        if (!user || user.password !== password) {
          return null;
        }

        return {
          id: user.id,
          email: user.email,
          name: user.display_name,
        };
      },
    })
  );
}

export const authOptions: NextAuthOptions = {
  providers,
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async jwt({ token, account }) {
      if (account?.access_token) {
        token.accessToken = account.access_token;
      }
      return token;
    },
    async session({ session, token }) {
      if (token.accessToken) {
        session.accessToken = token.accessToken as string;
      }
      return session;
    },
  },
};

// Extend NextAuth types
declare module "next-auth" {
  interface Session {
    accessToken?: string;
  }
}
