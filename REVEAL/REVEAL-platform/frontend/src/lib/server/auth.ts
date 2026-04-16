import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export async function requireSession() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.email) {
    throw new Error("UNAUTHORIZED");
  }
  return session;
}

export async function getCurrentUserRecord() {
  const session = await requireSession();
  const email = session.user?.email;
  if (!email) {
    throw new Error("UNAUTHORIZED");
  }
  const user = await prisma.user.findUnique({
    where: { email },
    include: {
      organization: true,
      sites: true,
    },
  });

  return { session, user };
}
