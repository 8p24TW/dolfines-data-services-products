import type { NextAuthOptions } from "next-auth";
import AzureADProvider from "next-auth/providers/azure-ad";
import CredentialsProvider from "next-auth/providers/credentials";
import GoogleProvider from "next-auth/providers/google";
import { prisma } from "@/lib/prisma";
import { verifyPassword } from "@/lib/server/passwords";

const azureConfigured = Boolean(
  process.env.AZURE_CLIENT_ID &&
  process.env.AZURE_CLIENT_SECRET &&
  process.env.AZURE_TENANT_ID
);

const googleConfigured = Boolean(
  process.env.GOOGLE_CLIENT_ID &&
  process.env.GOOGLE_CLIENT_SECRET
);

const providers: NextAuthOptions["providers"] = [];

async function ensureProvisionedUser(email: string, name?: string | null) {
  const normalizedEmail = email.trim().toLowerCase();
  const existingUser = await prisma.user.findUnique({
    where: { email: normalizedEmail },
  });

  if (existingUser) {
    if (name && existingUser.display_name !== name) {
      await prisma.user.update({
        where: { id: existingUser.id },
        data: { display_name: name },
      });
    }
    return existingUser;
  }

  const organization = await prisma.organization.upsert({
    where: { name: "External Access" },
    update: {},
    create: { name: "External Access" },
  });

  return prisma.user.create({
    data: {
      email: normalizedEmail,
      display_name: name?.trim() || normalizedEmail.split("@")[0] || "REVEAL user",
      plan_type: "unlimited",
      organizationId: organization.id,
    },
  });
}

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

if (googleConfigured) {
  providers.push(
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    })
  );
}

providers.push(
  CredentialsProvider({
    name: "Email Login",
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

      if (!user?.password) {
        return null;
      }

      const validPassword = await verifyPassword(password, user.password);
      if (!validPassword) {
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

export const authOptions: NextAuthOptions = {
  providers,
  session: {
    strategy: "jwt",
  },
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async signIn({ user, account }) {
      if (!user.email) {
        return false;
      }

      if (account?.provider && account.provider !== "credentials") {
        await ensureProvisionedUser(user.email, user.name);
      }

      return true;
    },
    async jwt({ token, account }) {
      if (account?.access_token) {
        token.accessToken = account.access_token;
      }

      if (token.email) {
        const dbUser = await prisma.user.findUnique({
          where: { email: token.email.toLowerCase() },
        });
        if (dbUser) {
          token.userId = dbUser.id;
          token.name = dbUser.display_name;
        }
      }

      return token;
    },
    async session({ session, token }) {
      if (token.accessToken) {
        session.accessToken = token.accessToken as string;
      }
      if (session.user) {
        if (token.userId) {
          session.user.id = token.userId as string;
        }
        if (token.name) {
          session.user.name = token.name as string;
        }
      }
      return session;
    },
  },
};

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    user?: {
      id?: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    userId?: string;
  }
}
