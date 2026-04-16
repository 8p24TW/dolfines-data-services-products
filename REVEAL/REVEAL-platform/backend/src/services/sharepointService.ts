import { ConfidentialClientApplication } from "@azure/msal-node";
import axios from "axios";

const msalConfig = {
  auth: {
    clientId: process.env.AZURE_SP_CLIENT_ID!,
    clientSecret: process.env.AZURE_SP_CLIENT_SECRET!,
    authority: `https://login.microsoftonline.com/${process.env.AZURE_SP_TENANT_ID!}`,
  },
};

const SP_HOST = process.env.SHAREPOINT_HOST!;
const SP_SITE_PATH = process.env.SHAREPOINT_SITE_PATH!;

let _msalApp: ConfidentialClientApplication | null = null;

function getMsalApp() {
  if (!_msalApp) _msalApp = new ConfidentialClientApplication(msalConfig);
  return _msalApp;
}

async function getToken(): Promise<string> {
  const result = await getMsalApp().acquireTokenByClientCredential({
    scopes: ["https://graph.microsoft.com/.default"],
  });
  if (!result?.accessToken) throw new Error("Failed to acquire SharePoint token");
  return result.accessToken;
}

async function getSiteId(token: string): Promise<string> {
  const { data } = await axios.get(
    `https://graph.microsoft.com/v1.0/sites/${SP_HOST}:${SP_SITE_PATH}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return data.id as string;
}

export const sharepointService = {
  async uploadFile(spPath: string, buffer: Buffer, filename: string): Promise<string> {
    const token = await getToken();
    const siteId = await getSiteId(token);

    const url = `https://graph.microsoft.com/v1.0/sites/${siteId}/drive/root:/${spPath}/${filename}:/content`;
    const { data } = await axios.put(url, buffer, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/octet-stream",
      },
    });
    return (data.webUrl as string) ?? "";
  },

  async downloadFile(spPath: string): Promise<Buffer> {
    const token = await getToken();
    const siteId = await getSiteId(token);

    const url = `https://graph.microsoft.com/v1.0/sites/${siteId}/drive/root:/${spPath}:/content`;
    const { data } = await axios.get<Buffer>(url, {
      headers: { Authorization: `Bearer ${token}` },
      responseType: "arraybuffer",
    });
    return Buffer.from(data);
  },

  async readJson<T>(spPath: string): Promise<T | null> {
    try {
      const buf = await this.downloadFile(spPath);
      return JSON.parse(buf.toString("utf-8")) as T;
    } catch {
      return null;
    }
  },

  async writeJson(spPath: string, filename: string, data: unknown): Promise<void> {
    const buf = Buffer.from(JSON.stringify(data, null, 2));
    await this.uploadFile(spPath, buf, filename);
  },
};
